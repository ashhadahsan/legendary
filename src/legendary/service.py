"""Shared application layer used by both the MCP server and the CLI."""

from __future__ import annotations

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


def remember(
    repo_root: Path,
    type: str,
    title: str,
    body: str,
    anchors: Optional[list[dict]] = None,
    tags: Optional[list[str]] = None,
    source: str = "agent",
) -> dict[str, Any]:
    """Validate, anchor-resolve, save, and index a new memory."""
    created = datetime.now(timezone.utc)
    resolved: list[Anchor] = []
    for raw in anchors or []:
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
    try:
        memory = Memory(
            id=Memory.new_id(title, created),
            type=type,  # type: ignore[arg-type]
            title=title,
            body=body,
            created=created,
            source=source,  # type: ignore[arg-type]
            anchors=resolved,
            tags=tags or [],
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    store.save(repo_root, memory)
    idx.rebuild(repo_root)
    return {
        "id": memory.id,
        "anchors": [a.model_dump(exclude_none=True) for a in resolved],
    }


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
    idx.rebuild(repo_root)
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
