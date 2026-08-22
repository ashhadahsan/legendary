"""Shared application layer used by both the MCP server and the CLI."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from legendary import index as idx
from legendary import rank, store
from legendary.anchor import resolve_and_hash
from legendary.models import Anchor, Memory
from legendary.stale import check_memory, worst_verdict

recall = rank.recall  # re-export: service.recall(repo_root, query, ...)


_TEST_NAME = re.compile(r"^test_\w+$")
_DIGIT_RUN = re.compile(r"\d{2,}|\d+\.\d+")


def _trigger_warnings(triggers: list[str]) -> list[str]:
    """Flag triggers that describe THIS occurrence rather than the failure.

    A trigger only works if it recurs byte-identically. Test names and specific
    numbers are exactly the parts that change: a memory keyed on
    `test_billing_reconciliation` and `assert 0.0 == 25.0` never fires again
    when the next failure is `test_refund_reconciliation` / `assert 0.0 == 20.0`.
    Observed in real trials. Warn, never block - the memory is still worth
    storing.
    """
    out = []
    for trig in triggers:
        s = trig.strip()
        if _TEST_NAME.match(s):
            out.append(
                f"{trig!r} is a test name, which changes between failures. "
                "Prefer the exception type and message that will repeat."
            )
        elif _DIGIT_RUN.search(s):
            out.append(
                f"{trig!r} contains specific numbers, which usually differ next "
                "time. Prefer the invariant part of the message."
            )
    return out


def remember(
    repo_root: Path,
    type: str,
    title: str,
    body: str,
    anchors: Optional[list[dict]] = None,
    tags: Optional[list[str]] = None,
    source: str = "agent",
    supersedes: Optional[str] = None,
    transcript: Optional[str] = None,
    triggers: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Validate, anchor-resolve, save, and index a new memory."""
    created = datetime.now(timezone.utc)
    old: Optional[Memory] = None
    if supersedes is not None:
        old = store.load(repo_root, supersedes)
        if old is None:
            raise ValueError(f"no such memory to supersede: {supersedes}")
    if type == "episode" and not triggers:
        raise ValueError(
            "episode memories must include triggers: the verbatim error string "
            "or failing test name you observed (e.g. 'sqlite3.OperationalError: "
            "database is locked'). Triggers are what let this memory resurface "
            "when the same failure happens again."
        )
    resolved: list[Anchor] = []
    for raw in anchors or []:
        if not isinstance(raw, dict):
            # LLM extraction sometimes emits ["src/foo.py"] instead of
            # [{"file": "src/foo.py"}]; Anchor(**raw) would raise TypeError,
            # which neither guard layer catches.
            raise ValueError(
                # NB: `type` is a parameter of this function, so type(raw) would
                # call the string. Use __class__ instead.
                f"anchor must be an object, got {raw.__class__.__name__}: {raw!r}"
            )
        try:
            anchor = Anchor(**raw)
        except ValidationError as exc:
            raise ValueError(f"invalid anchor {raw}: {exc}") from exc
        try:
            resolved.append(resolve_and_hash(repo_root, anchor))
        except FileNotFoundError as exc:
            raise ValueError(
                f"anchor file not found: {anchor.file} - "
                "check the path or retry with a line range"
            ) from exc
    if old is not None:
        missing = {a.file for a in old.anchors} - {a.file for a in resolved}
        if missing:
            raise ValueError(
                f"supersede blocked: the new memory does not cover anchors "
                f"{sorted(missing)} of {old.id}. Anchor the replacement to those "
                "files too, or use deprecate(reason=...) instead of supersedes."
            )
    try:
        memory = Memory(
            id=Memory.new_id(title, created),
            type=type,
            title=title,
            body=body,
            created=created,
            source=source,
            anchors=resolved,
            tags=tags or [],
            transcript=transcript,
            triggers=triggers or [],
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    store.save(repo_root, memory)
    idx.upsert(repo_root, memory)
    if old is not None:
        superseded = old.model_copy(
            update={
                "status": "deprecated",
                "deprecated_reason": f"superseded by {memory.id}",
                "superseded_by": memory.id,
            }
        )
        store.save(repo_root, superseded)
        idx.upsert(repo_root, superseded)
    result: dict[str, Any] = {
        "id": memory.id,
        "anchors": [a.model_dump(exclude_none=True) for a in resolved],
    }
    warnings = _trigger_warnings(triggers or [])
    if warnings:
        result["trigger_warnings"] = warnings
    return result


def list_memories(
    repo_root: Path,
    type: Optional[str] = None,
    tag: Optional[str] = None,
    file: Optional[str] = None,
    include_deprecated: bool = False,
) -> list[dict[str, Any]]:
    out = []
    for m in store.load_all(repo_root):
        if not include_deprecated and m.status != "active":
            continue
        if type and m.type != type:
            continue
        if tag and tag not in m.tags:
            continue
        if file and file not in {a.file for a in m.anchors}:
            continue
        out.append(
            {
                "id": m.id,
                "type": m.type,
                "title": m.title,
                "tags": m.tags,
                "created": m.created.isoformat(),
            }
        )
    return out


def deprecate(repo_root: Path, memory_id: str, reason: str) -> dict[str, Any]:
    m = store.load(repo_root, memory_id)
    if m is None:
        raise ValueError(f"no such memory: {memory_id}")
    m = m.model_copy(update={"status": "deprecated", "deprecated_reason": reason})
    store.save(repo_root, m)
    idx.upsert(repo_root, m)
    return {"id": memory_id, "status": "deprecated"}


def stale_report(repo_root: Path) -> list[dict[str, Any]]:
    """All active memories whose worst anchor verdict is not fresh."""
    out = []
    for m in store.load_all(repo_root):
        if m.status != "active" or not m.anchors:
            continue
        verdicts = check_memory(repo_root, m.anchors)
        worst = worst_verdict(verdicts)
        if worst != "fresh":
            out.append(
                {
                    "id": m.id,
                    "title": m.title,
                    "staleness": worst,
                    "anchors": [
                        {**a.model_dump(exclude_none=True), "staleness": v}
                        for a, v in zip(m.anchors, verdicts)
                    ],
                }
            )
    return out
