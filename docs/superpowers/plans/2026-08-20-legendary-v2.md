# Legendary v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Invert legendary from a memory database into a delivery-and-verification layer: push-based just-in-time injection by default, error-signature triggers, imperative payloads, ~55% of the code deleted, and a structurally ungameable benchmark.

**Architecture:** Hooks (PreToolUse `surface`, new PostToolUse `guard`) become the primary channel, installed by `init`; MCP (`recall`/`remember`/`deprecate` only) is the add-on. Memory model shrinks to `decision|episode`, gains indexed `triggers` (required for episodes), and `supersedes` is coverage-gated. Ranking drops recency and config tunables. The staleness engine is untouched.

**Tech Stack:** Unchanged — Python 3.12, uv, pydantic v2, mcp 2.x, tree-sitter-language-pack, stdlib sqlite3 FTS5.

**Spec:** `docs/superpowers/specs/2026-08-20-legendary-v2-design.md`

**Baseline:** branch `main` at v0.1.1+, suite currently **110 passed**. Work on branch `feat/legendary-v2`. Every task ends with the full gate: `uv run ruff format --check src tests bench && uv run ruff check src tests bench && uv run mypy && uv run pytest -q`.

**Commit rule:** plain messages, NEVER any Co-Authored-By/AI-attribution trailer.

---

### Task 0: Branch

- [ ] **Step 1:** `git checkout main && git pull -q && git checkout -b feat/legendary-v2`
- [ ] **Step 2:** Run `uv run pytest -q` — Expected: `110 passed`.

---

### Task 1: Delete `extract` and `inject`

**Files:**
- Delete: `src/legendary/extract.py`, `tests/test_extract.py`
- Modify: `src/legendary/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: Delete the files**

```bash
git rm -q src/legendary/extract.py tests/test_extract.py
```

- [ ] **Step 2: Remove the commands from cli.py**

Delete the entire `_cmd_extract` and `_cmd_inject` functions. In `main()`, delete these registration lines:

```python
    p_extract = _add_repo(sub.add_parser("extract"))
    p_extract.add_argument("transcript", nargs="?", default=None)
    p_inject = _add_repo(sub.add_parser("inject"))
    p_inject.add_argument("-k", type=int, default=5)
```

and these match arms:

```python
        case "extract":
            return _cmd_extract(repo, args.transcript)
        case "inject":
            return _cmd_inject(repo, args.k)
```

In `_MCP_SNIPPET`, delete the `SessionStart` and `SessionEnd` hook entries (keep the `PreToolUse` entry), and change the `_cmd_init` print call from `print(_MCP_SNIPPET % (repo, repo, repo, repo))` to `print(_MCP_SNIPPET % (repo, repo))`. Update the module docstring's command list to `init | search | reindex | doctor | surface | mcp`.

- [ ] **Step 3: Remove the inject tests**

In `tests/test_cli.py` delete `test_inject_prints_memories` and `test_inject_empty_repo_prints_nothing`. In `test_init_scaffolds`, delete the line `assert "SessionEnd" in out  # prints hook snippet` (Task 10 rewrites init's output and its tests properly).

- [ ] **Step 4: Gate**

Run: `uv run ruff format --check src tests bench && uv run ruff check src tests bench && uv run mypy && uv run pytest -q`
Expected: all green, `103 passed`.

- [ ] **Step 5: Commit** — `git commit -am "refactor!: delete extract and inject (write-side sophistication, wrong-timing injection)"`

---

### Task 2: Memory model — `decision|episode` only, legacy coercion, `triggers`

**Files:**
- Modify: `src/legendary/models.py`
- Test: `tests/test_models.py` (append)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_models.py`)

```python
def test_legacy_types_coerce_to_decision():
    # v0.1 stores may contain convention/reference; they must load, not vanish
    for legacy in ("convention", "reference"):
        m = Memory(
            id="mem-legacy",
            type=legacy,
            title="old memory",
            body="body",
            created=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        assert m.type == "decision"


def test_triggers_round_trip():
    m = Memory(
        id="mem-trig",
        type="episode",
        title="locked db",
        body="body",
        created=datetime(2026, 8, 1, tzinfo=timezone.utc),
        triggers=["sqlite3.OperationalError: database is locked"],
    )
    loaded = Memory.from_markdown(m.to_markdown())
    assert loaded.triggers == ["sqlite3.OperationalError: database is locked"]
```

(`datetime`/`timezone` are already imported in this test file; if not, add `from datetime import datetime, timezone`.)

- [ ] **Step 2:** Run `uv run pytest tests/test_models.py -q` — Expected: FAIL (coercion missing; unknown field `triggers`).

- [ ] **Step 3: Implement in models.py**

Change the type alias:

```python
MemoryType = Literal["decision", "episode"]
```

Add the field after `tags`:

```python
    triggers: list[str] = Field(default_factory=list)
```

Add a before-validator next to `_ensure_aware`:

```python
    @field_validator("type", mode="before")
    @classmethod
    def _coerce_legacy_type(cls, v: object) -> object:
        """v0.1 stores may contain convention/reference; both were declarative
        knowledge, so they load as decision instead of failing validation and
        silently vanishing from load_all."""
        if v in ("convention", "reference"):
            return "decision"
        return v
```

- [ ] **Step 4:** In `tests/test_review_fixes.py::test_unicode_round_trips_through_the_store`, change `type="convention"` to `type="decision"` (the coercion makes the old value legal but the test should use a real type).

- [ ] **Step 5: Gate** — Expected: `105 passed`.
- [ ] **Step 6: Commit** — `git commit -am "feat!: memory types are decision|episode; legacy types coerce; triggers field"`

---

### Task 3: Service + MCP — episode-trigger enforcement, 3-tool surface, stdio only

**Files:**
- Modify: `src/legendary/service.py`, `src/legendary/mcp_server.py`, `src/legendary/cli.py`
- Test: `tests/test_service.py`, `tests/test_mcp_server.py`, `tests/test_polish.py`, `tests/test_cli.py`, `tests/test_review_fixes.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_service.py`)

```python
def test_episode_without_triggers_rejected(repo: Path):
    with pytest.raises(ValueError, match="triggers"):
        service.remember(
            repo_root=repo, type="episode", title="x", body="y", anchors=[]
        )


def test_episode_with_triggers_saved(repo: Path):
    result = service.remember(
        repo_root=repo,
        type="episode",
        title="locked",
        body="y",
        anchors=[],
        triggers=["database is locked"],
    )
    assert load(repo, result["id"]).triggers == ["database is locked"]
```

Append to `tests/test_mcp_server.py`:

```python
def test_mcp_surface_is_exactly_three_tools(repo: Path):
    tools = asyncio.run(build_server(repo).list_tools())
    assert {t.name for t in tools} == {"remember", "recall", "deprecate"}
```

- [ ] **Step 2:** Run `uv run pytest tests/test_service.py tests/test_mcp_server.py -q` — Expected: FAIL.

- [ ] **Step 3: service.py** — add `triggers: Optional[list[str]] = None` to `remember`'s signature (after `supersedes`). Immediately after the `supersedes` lookup block, add:

```python
    if type == "episode" and not triggers:
        raise ValueError(
            "episode memories must include triggers: the verbatim error string "
            "or failing test name you observed (e.g. 'sqlite3.OperationalError: "
            "database is locked'). Triggers are what let this memory resurface "
            "when the same failure happens again."
        )
```

Pass `triggers=triggers or []` into the `Memory(...)` constructor.

- [ ] **Step 4: mcp_server.py** — delete the `stale_report` tool entirely. Add `triggers: Optional[list[str]] = None` to the `remember` tool signature and pass it through; extend its docstring with: `"episode requires triggers: the verbatim error/test-failure strings observed."`. Replace the whole `run()` function with:

```python
def run(repo_root: Path) -> None:
    """Serve the MCP tools over stdio."""
    build_server(repo_root).run()
```

(and delete the `anyio` import path). Update `build_server`'s `instructions` to:

```python
        instructions=(
            "Repo memory. `recall` before editing a file; `remember` decisions "
            "and failed attempts (episodes need verbatim error strings as "
            "triggers). 'stale' means the anchored code changed - verify."
        ),
```

- [ ] **Step 5: cli.py** — the `mcp` subparser loses `--transport/--host/--port`: registration becomes `_add_repo(sub.add_parser("mcp"))`, the match arm becomes `return _cmd_mcp(repo)`, and:

```python
def _cmd_mcp(repo: Path) -> int:
    from legendary.mcp_server import run

    run(repo)
    return 0
```

- [ ] **Step 6: Update existing episode-writing tests** (mechanical; each keeps its assertions):
  - `tests/test_service.py` `remember_one` defaults: add `triggers=["sqlite3.OperationalError: database is locked"],`
  - `tests/test_polish.py` `remember_one` defaults: add the same `triggers=[...]` line
  - `tests/test_cli.py` `seed()`: add the same `triggers=[...]` argument
  - `tests/test_mcp_server.py` `test_remember_then_recall_end_to_end`: add `"triggers": ["database is locked"],` to the remember args; `test_remember_bad_anchor_surfaces_error`: add the same key
  - `tests/test_mcp_server.py` `test_all_five_tools_registered`: delete (replaced by the three-tool test); `test_tool_schemas_expose_parameters` keeps working unchanged
  - `tests/test_review_fixes.py`: `test_non_dict_anchor_raises_value_error_not_type_error` — change `type="episode"` to `type="decision"`; `test_stemming_matches_word_forms`, `test_mcp_recall_omits_internal_fields`, `test_mcp_recall_reports_commit_when_stale` — add `triggers=["database is locked"],` to their `service.remember` calls

- [ ] **Step 7: Gate** — Expected: `107 passed` (105 − test_all_five_tools + 3 new).
- [ ] **Step 8: Commit** — `git commit -am "feat!: episodes require triggers; MCP surface is recall/remember/deprecate over stdio"`

---

### Task 4: Ranking — fixed weights, no recency, no config

**Files:**
- Modify: `src/legendary/rank.py`
- Test: `tests/test_rank.py`, `tests/test_review_fixes.py`

- [ ] **Step 1: Rewrite rank.py** to exactly:

```python
"""Recall: FTS search -> staleness check -> weighted ranking."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from legendary import index as idx
from legendary.stale import check_memory, worst_verdict
from legendary.store import load

# Fixed weights. Recency is deliberately absent: an old memory whose anchor
# still hashes fresh SURVIVED - recency would double-penalize durability, and
# staleness already measures drift. Config tunables were deleted with it:
# nobody tunes four floats over a store of a few dozen memories.
WEIGHTS = {"fts": 2.0, "overlap": 1.5, "stale": 1.0}
_STALE_PENALTY = {"fresh": 0.0, "stale": 0.5, "orphaned": 0.8}


def _normalize_focus(repo_root: Path, files_in_focus: Optional[list[str]]) -> set[str]:
    """Hosts pass absolute paths; anchors store repo-relative posix paths.
    Exact string intersection between the two silently loses the overlap
    boost, so normalize before matching."""
    focus: set[str] = set()
    root = repo_root.resolve()
    for f in files_in_focus or []:
        p = Path(f)
        if p.is_absolute():
            try:
                focus.add(p.resolve().relative_to(root).as_posix())
                continue
            except ValueError:
                pass  # outside the repo: keep the raw string as a last resort
        focus.add(p.as_posix())
    return focus


def recall(
    repo_root: Path,
    query: str,
    files_in_focus: Optional[list[str]] = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Return top-k memories as dicts with staleness flags and anchor citations."""
    focus = _normalize_focus(repo_root, files_in_focus)
    # fetch a wider candidate pool than k: ranking reorders by staleness and
    # focus overlap, so the FTS top-k is not the final top-k
    hits = idx.search(repo_root, query, limit=max(50, k * 10))
    if not hits:
        return []
    max_rel = max(rel for _, rel in hits) or 1.0

    results: list[dict[str, Any]] = []
    for memory_id, rel in hits:
        m = load(repo_root, memory_id)
        if m is None or m.status != "active":
            continue
        verdicts = check_memory(repo_root, m.anchors)
        worst = worst_verdict(verdicts)
        anchor_files = {a.file for a in m.anchors}
        overlap = 1.0 if focus & anchor_files else 0.0
        score = (
            WEIGHTS["fts"] * (rel / max_rel)
            + WEIGHTS["overlap"] * overlap
            - WEIGHTS["stale"] * _STALE_PENALTY[worst]
        )
        results.append(
            {
                "id": m.id,
                "type": m.type,
                "title": m.title,
                "body": m.body,
                "tags": m.tags,
                "staleness": worst,
                "anchors": [
                    {**a.model_dump(exclude_none=True), "staleness": v}
                    for a, v in zip(m.anchors, verdicts)
                ],
                "score": round(score, 4),
            }
        )
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]
```

- [ ] **Step 2: Update tests.** In `tests/test_rank.py`: delete `test_recency_breaks_ties`, `test_config_toml_weights_are_applied`, `test_malformed_config_falls_back_to_defaults`; delete the `NOW = ...` constant, the `created` parameter of `mk`, and every `now=NOW`/`created=` argument in remaining tests (the four survivors: ranked_results, focus_boost, stale_below_fresh, k_limits). Add:

```python
def test_absolute_focus_paths_still_boost(repo: Path):
    mk(repo, "mem-1", "sync focus note", "same body", file="src/sync/worker.py")
    mk(repo, "mem-2", "sync focus note two", "same body")
    rebuild(repo)
    results = recall(
        repo, "focus note", files_in_focus=[str(repo / "src/sync/worker.py")]
    )
    assert results[0]["id"] == "mem-1"
```

In `tests/test_review_fixes.py`: `test_naive_created_does_not_break_recall` — drop the `now=` argument from its `recall` call (the naive-datetime coercion assertion and index round-trip still exercise the fix); `test_recall_k_above_default_limit_is_honoured` — its `recall` call has no `now`, unchanged.

- [ ] **Step 3: Gate** — Expected: `105 passed` (107 − 3 deleted + 1 added).
- [ ] **Step 4: Commit** — `git commit -am "feat!: fixed ranking weights, recency and config tunables removed, focus paths normalized"`

---

### Task 5: Coverage-gated `supersedes`

**Files:**
- Modify: `src/legendary/service.py`
- Test: `tests/test_polish.py` (append)

- [ ] **Step 1: Failing tests** (append to `tests/test_polish.py`)

```python
def test_supersede_requires_anchor_coverage(repo: Path):
    # Observed in trial forensics: a narrow memory deprecated a broader one,
    # leaving a file with no active memory. Coverage must be enforced.
    old_id = service.remember(
        repo_root=repo,
        type="decision",
        title="broad rule",
        body="applies to worker",
        anchors=[{"file": "src/sync/worker.py"}],
    )["id"]
    with pytest.raises(ValueError, match="src/sync/worker.py"):
        service.remember(
            repo_root=repo,
            type="decision",
            title="narrow rule",
            body="applies to nothing",
            anchors=[],
            supersedes=old_id,
        )
    assert load(repo, old_id).status == "active"  # nothing was destroyed


def test_supersede_with_coverage_succeeds(repo: Path):
    old_id = service.remember(
        repo_root=repo,
        type="decision",
        title="broad rule two",
        body="worker rule",
        anchors=[{"file": "src/sync/worker.py"}],
    )["id"]
    new_id = service.remember(
        repo_root=repo,
        type="decision",
        title="broader rule",
        body="worker rule refined",
        anchors=[{"file": "src/sync/worker.py"}],
        supersedes=old_id,
    )["id"]
    assert load(repo, old_id).superseded_by == new_id
```

- [ ] **Step 2:** Run them — Expected: first test FAILS (no coverage check yet).

- [ ] **Step 3: Implement.** In `service.remember`, after the anchors are resolved (the `resolved` list is complete) and before the `Memory(...)` construction, add:

```python
    if old is not None:
        missing = {a.file for a in old.anchors} - {a.file for a in resolved}
        if missing:
            raise ValueError(
                f"supersede blocked: the new memory does not cover anchors "
                f"{sorted(missing)} of {old.id}. Anchor the replacement to those "
                "files too, or use deprecate(reason=...) instead of supersedes."
            )
```

- [ ] **Step 4: Gate** — Expected: `107 passed`.
- [ ] **Step 5: Commit** — `git commit -am "fix!: supersedes requires anchor coverage - corrections must not destroy knowledge"`

---

### Task 6: Index schema v3 — trigger table

**Files:**
- Modify: `src/legendary/index.py`
- Test: `tests/test_index.py` (append)

- [ ] **Step 1: Failing test** (append to `tests/test_index.py`)

```python
def test_triggers_indexed_for_active_memories(repo: Path):
    from legendary.index import all_triggers

    save(
        repo,
        mem("mem-t", "locked episode", "body").model_copy(
            update={"type": "episode", "triggers": ["database is locked"]}
        ),
    )
    save(repo, mem("mem-d", "dead note", "body", status="deprecated"))
    rebuild(repo)
    assert all_triggers(repo) == [("mem-t", "database is locked")]
```

- [ ] **Step 2:** Run it — Expected: FAIL (`all_triggers` missing).

- [ ] **Step 3: Implement in index.py.** Bump `_SCHEMA_VERSION = 3`. Append to `_SCHEMA`:

```sql
CREATE TABLE IF NOT EXISTS mem_triggers (
    memory_id TEXT, trigger TEXT
);
```

In `_migrate`, add `conn.execute("DROP TABLE IF EXISTS mem_triggers")` beside the other drops. In `_delete_rows`, add `conn.execute("DELETE FROM mem_triggers WHERE memory_id = ?", (memory_id,))`. In `_insert_rows`, add:

```python
    for trig in m.triggers:
        conn.execute("INSERT INTO mem_triggers VALUES (?,?)", (m.id, trig))
```

In `rebuild`, add `conn.execute("DELETE FROM mem_triggers")` beside the other deletes. Add at module bottom:

```python
def all_triggers(repo_root: Path) -> list[tuple[str, str]]:
    """(memory_id, trigger) pairs for active memories, for guard matching."""
    conn = _ensure_populated(repo_root, _connect(repo_root))
    try:
        rows = conn.execute(
            """
            SELECT t.memory_id, t.trigger FROM mem_triggers t
            JOIN mem_meta m ON m.id = t.memory_id
            WHERE m.status = 'active'
            ORDER BY t.memory_id, t.trigger
            """
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    finally:
        conn.close()
```

- [ ] **Step 4: Gate** — Expected: `108 passed` (the existing schema-migration regression test now asserts version 3 automatically via `_SCHEMA_VERSION`).
- [ ] **Step 5: Commit** — `git commit -am "feat: index memory triggers (schema v3) for error-signature matching"`

---

### Task 7: Imperative rendering in `surface`

**Files:**
- Modify: `src/legendary/cli.py`
- Test: `tests/test_polish.py`

- [ ] **Step 1: Failing test** (append to `tests/test_polish.py`)

```python
def test_surface_fresh_memory_is_marked_verified(repo: Path, monkeypatch, capsys):
    remember_one(repo)
    _, out = surface(repo, monkeypatch, capsys, "src/sync/worker.py")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "(verified against current code)" in ctx
```

- [ ] **Step 2:** Run it — Expected: FAIL.

- [ ] **Step 3: Implement.** In `cli.py`, add a module-level helper above `_cmd_surface`:

```python
def _render_memory(m: object, verdict: str) -> str:
    """Imperative guardrail rendering shared by surface and guard.

    Fresh carries the affordance that licenses acting without re-derivation;
    stale carries the instruction to verify. Both are the product's voice."""
    title = getattr(m, "title")
    body = getattr(m, "body")[:300]
    mtype = getattr(m, "type")
    if verdict == "fresh":
        return f"- [{mtype}] {title} (verified against current code): {body}"
    return (
        f"- [{mtype}] {title} [{verdict} - code changed since this was "
        f"written; verify before trusting]: {body}"
    )
```

In `_cmd_surface`, replace the `flag = ...` / `lines.append(...)` pair with:

```python
        lines.append(_render_memory(m, verdict))
```

- [ ] **Step 4:** Update `tests/test_polish.py::test_surface_flags_stale_memories`: the assertion `"stale" in ...` still passes unchanged (the word appears in the new rendering); no edit needed — verify by running it.

- [ ] **Step 5: Gate** — Expected: `109 passed`.
- [ ] **Step 6: Commit** — `git commit -am "feat: imperative guardrail rendering with verified/stale affordances"`

---

### Task 8: `guard` — PostToolUse error-signature injection

**Files:**
- Modify: `src/legendary/cli.py`
- Test: `tests/test_guard.py` (create)

- [ ] **Step 1: Failing tests** (create `tests/test_guard.py`)

```python
import io
import json
from pathlib import Path

from legendary import cli, service


def seed_episode(repo: Path):
    return service.remember(
        repo_root=repo,
        type="episode",
        title="deferred BEGIN deadlocks",
        body="Use BEGIN IMMEDIATE; busy_timeout cannot fix a write-write conflict.",
        anchors=[{"file": "src/sync/worker.py"}],
        triggers=["sqlite3.OperationalError: database is locked"],
    )["id"]


def guard(repo: Path, monkeypatch, capsys, output: str, session: str = "g1"):
    payload = {
        "session_id": session,
        "tool_name": "Bash",
        "tool_response": {"stdout": output, "stderr": ""},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code = cli.main(["guard", "--repo", str(repo)])
    return code, capsys.readouterr().out


def test_guard_injects_on_matching_error(repo: Path, monkeypatch, capsys):
    seed_episode(repo)
    code, out = guard(
        repo,
        monkeypatch,
        capsys,
        "FAILED tests/x.py - sqlite3.OperationalError: database is locked",
    )
    assert code == 0
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PostToolUse"
    assert "BEGIN IMMEDIATE" in payload["additionalContext"]


def test_guard_silent_on_unrelated_output(repo: Path, monkeypatch, capsys):
    seed_episode(repo)
    _, out = guard(repo, monkeypatch, capsys, "3 passed in 0.12s")
    assert out.strip() == ""


def test_guard_dedupes_within_session(repo: Path, monkeypatch, capsys):
    seed_episode(repo)
    err = "sqlite3.OperationalError: database is locked"
    guard(repo, monkeypatch, capsys, err, session="g2")
    _, out2 = guard(repo, monkeypatch, capsys, err, session="g2")
    assert out2.strip() == ""


def test_guard_garbage_stdin_exits_zero(repo: Path, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert cli.main(["guard", "--repo", str(repo)]) == 0
```

- [ ] **Step 2:** Run `uv run pytest tests/test_guard.py -q` — Expected: FAIL (`unrecognized arguments`/exit 2 wrapped by argparse → collection-level failures are acceptable evidence).

- [ ] **Step 3: Implement `_cmd_guard`** in `cli.py` (below `_cmd_surface`):

```python
def _cmd_guard(repo: Path) -> int:
    """PostToolUse hook on Bash: inject episodes whose triggers match output.

    A recurring error string is the highest-fidelity experience-following
    signal an agent emits - no query formulation needed. Any internal failure
    exits 0: a broken hook must never break the agent.
    """
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return 0
    if hook.get("tool_name") != "Bash":
        return 0
    haystack = json.dumps(hook.get("tool_response") or {}).lower()
    if not haystack or haystack == "{}":
        return 0
    from legendary.index import all_triggers

    matched_ids = {
        mid for mid, trig in all_triggers(repo) if trig.lower() in haystack
    }
    if not matched_ids:
        return 0
    session = hook.get("session_id") or "default"
    cache = repo / ".legendary" / f".surfaced-{session}"
    seen = set(cache.read_text().split()) if cache.exists() else set()
    new_ids = sorted(matched_ids - seen)
    if not new_ids:
        return 0
    from legendary.stale import check_memory, worst_verdict
    from legendary.store import load

    lines = []
    rendered: list[str] = []
    for mid in new_ids[:3]:
        m = load(repo, mid)
        if m is None or m.status != "active":
            continue
        verdict = worst_verdict(check_memory(repo, m.anchors))
        lines.append(_render_memory(m, verdict))
        rendered.append(mid)
    if not lines:
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(" ".join(sorted(seen | set(rendered))))
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        "This failure has been seen before. Recorded episodes:\n"
                        + "\n".join(lines)
                    ),
                }
            }
        )
    )
    return 0
```

Register in `main()`: `_add_repo(sub.add_parser("guard"))` beside the `surface` registration, and add the match arm `case "guard": return _cmd_guard(repo)`. Update the module docstring command list to include `guard`.

- [ ] **Step 4: Gate** — Expected: `113 passed`.
- [ ] **Step 5: Commit** — `git commit -am "feat: guard hook - inject episodes when their error signatures reappear"`

---

### Task 9: `init` installs hooks by default

**Files:**
- Modify: `src/legendary/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Failing tests.** In `tests/test_cli.py`, replace `test_init_scaffolds` and `test_init_twice_is_safe` with:

```python
def test_init_scaffolds_and_installs_hooks(repo: Path, capsys):
    code, out = run_cli("init", cwd=repo, capsys=capsys)
    assert code == 0
    assert (repo / ".legendary" / "memories").is_dir()
    assert ".legendary/index.db" in (repo / ".gitignore").read_text()
    settings = json.loads((repo / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]
    assert any(
        "legendary surface" in h["hooks"][0]["command"] for h in hooks["PreToolUse"]
    )
    assert any(
        "legendary guard" in h["hooks"][0]["command"] for h in hooks["PostToolUse"]
    )
    assert "mcpServers" in out  # MCP remains available as the printed add-on


def test_init_twice_is_safe_and_idempotent(repo: Path, capsys):
    assert run_cli("init", cwd=repo, capsys=capsys)[0] == 0
    assert run_cli("init", cwd=repo, capsys=capsys)[0] == 0
    assert (repo / ".gitignore").read_text().count(".legendary/index.db") == 1
    settings = json.loads((repo / ".claude" / "settings.json").read_text())
    assert len(settings["hooks"]["PreToolUse"]) == 1  # not duplicated


def test_init_preserves_existing_user_hooks(repo: Path, capsys):
    claude = repo / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [{"type": "command", "command": "echo mine"}],
                        }
                    ]
                },
                "env": {"FOO": "1"},
            }
        )
    )
    run_cli("init", cwd=repo, capsys=capsys)
    settings = json.loads((claude / "settings.json").read_text())
    assert settings["env"] == {"FOO": "1"}  # untouched
    commands = [
        h["hooks"][0]["command"] for h in settings["hooks"]["PreToolUse"]
    ]
    assert "echo mine" in commands
    assert any("legendary surface" in c for c in commands)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_cli.py -q` — Expected: FAIL.

- [ ] **Step 3: Implement.** In `cli.py`, replace `_CONFIG_TOML` (delete it — config.toml is no longer written; ranking has no tunables) and `_MCP_SNIPPET` with:

```python
_MCP_SNIPPET = """\
Hooks installed in .claude/settings.json (primary channel - memories arrive
automatically). Optional add-on, agent-initiated search via MCP (.mcp.json):

{
  "mcpServers": {
    "legendary": {
      "command": "uvx",
      "args": ["--from", "legendary-mcp", "legendary", "mcp", "--repo", "%s"]
    }
  }
}

Suggested CLAUDE.md line:
  When an approach fails, call the legendary `remember` tool with type=episode
  and the verbatim error string as a trigger.
"""
```

Add above `_cmd_init`:

```python
def _install_hooks(repo: Path) -> None:
    """Merge legendary's hooks into .claude/settings.json, idempotently.

    Never clobbers user configuration: unknown keys and existing hook entries
    are preserved; our entries are recognized by their command substring."""
    settings_path = repo / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError):
        settings = {}
    hooks = settings.setdefault("hooks", {})
    wanted = {
        "PreToolUse": (
            "Read|Edit|Write",
            f"uvx --from legendary-mcp legendary surface --repo {repo}",
        ),
        "PostToolUse": (
            "Bash",
            f"uvx --from legendary-mcp legendary guard --repo {repo}",
        ),
    }
    for event, (matcher, command) in wanted.items():
        entries = hooks.setdefault(event, [])
        marker = command.split(" --repo ")[0]
        if not any(
            marker in h.get("command", "")
            for e in entries
            for h in e.get("hooks", [])
        ):
            entries.append(
                {"matcher": matcher, "hooks": [{"type": "command", "command": command}]}
            )
    settings_path.parent.mkdir(exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
```

Rewrite `_cmd_init` to:

```python
def _cmd_init(repo: Path) -> int:
    if not (repo / ".git").exists():
        print(
            f"error: {repo} is not a git repository (run `git init` first)",
            file=sys.stderr,
        )
        return 1
    (repo / ".legendary" / "memories").mkdir(parents=True, exist_ok=True)
    gitignore = repo / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    additions = [
        e
        for e in (".legendary/index.db", ".legendary/.surfaced-*")
        if e not in existing
    ]
    if additions:
        gitignore.write_text(
            existing.rstrip("\n")
            + ("\n" if existing else "")
            + "\n".join(additions)
            + "\n"
        )
    _install_hooks(repo)
    idx.rebuild(repo)
    print(f"initialized .legendary/ in {repo}\n")
    print(_MCP_SNIPPET % repo)
    return 0
```

- [ ] **Step 4: Gate** — Expected: `114 passed` (113 − 2 replaced + 3 new).
- [ ] **Step 5: Commit** — `git commit -am "feat!: init installs surface+guard hooks by default; MCP becomes the add-on"`

---

### Task 10: Line count + dead-code sweep

- [ ] **Step 1:** Run `uv run ruff check src tests --select F401,F811` and `grep -rn "tomllib\|_load_weights\|stale_report\|transport\|extract_from_transcript" src/legendary/` — remove any stragglers found (imports, docstrings, README strings in `cli.py`).
- [ ] **Step 2:** Run `wc -l src/legendary/*.py` — Expected: total in the 600–800 range (down from ~1,310).
- [ ] **Step 3: Gate**, then `git commit -am "chore: dead-code sweep after v2 cuts"` (skip commit if no changes).

---

### Task 11: Benchmark v2 fixture — opaque service

**Files:**
- Create: `bench/mockpay.py`, `bench/scenario2/pyproject.toml`, `bench/scenario2/billing/__init__.py`, `bench/scenario2/billing/client.py`, `bench/scenario2/billing/refunds.py`, `bench/scenario2/tests/test_billing.py`, `bench/scenario2/tests/test_refunds.py`
- Delete: `bench/scenario/` (retired fixture — reproduces retracted defects)

- [ ] **Step 1: Create `bench/mockpay.py`** (harness-owned; never copied into trial repos):

```python
#!/usr/bin/env python3
"""Opaque payments mock for the v2 benchmark. Lives OUTSIDE trial repos.

The quirk (modeled on real payment APIs): any record whose `amount` is a JSON
float is SILENTLY DROPPED - the response is still 200 {"status": "accepted"}.
Amounts must be string decimals. The quirk is only discoverable by experiment,
and every request is logged so dead ends are measured behaviorally.
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    log_path: Path
    totals: dict[str, float] = {"batch": 0.0, "refund": 0.0}

    def log_message(self, *args: object) -> None:  # silence stderr noise
        pass

    def _log(self, endpoint: str, records: list, dropped: int) -> None:
        with _LOCK:
            with self.log_path.open("a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "endpoint": endpoint,
                            "n_records": len(records),
                            "n_dropped_float": dropped,
                        }
                    )
                    + "\n"
                )

    def _reply(self, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        endpoint = self.path.strip("/")
        if endpoint not in ("batch", "refund"):
            self._reply({"status": "unknown endpoint"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            records = json.loads(self.rfile.read(length))["records"]
        except Exception:
            self._reply({"status": "bad request"})
            return
        dropped = 0
        with _LOCK:
            for rec in records:
                amount = rec.get("amount")
                # THE QUIRK: float amounts vanish, response says accepted anyway
                if isinstance(amount, float):
                    dropped += 1
                    continue
                try:
                    Handler.totals[endpoint] += float(str(amount))
                except (TypeError, ValueError):
                    dropped += 1
        self._log(endpoint, records, dropped)
        self._reply({"status": "accepted"})

    def do_GET(self) -> None:
        if self.path == "/totals":
            with _LOCK:
                self._reply(dict(Handler.totals))
        elif self.path == "/reset":
            with _LOCK:
                Handler.totals = {"batch": 0.0, "refund": 0.0}
            self._reply({"status": "reset"})
        else:
            self._reply({"status": "unknown endpoint"})


def main() -> int:
    port = int(sys.argv[1])
    Handler.log_path = Path(sys.argv[2])
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Create the scenario repo** (`bench/scenario2/`):

`pyproject.toml`:

```toml
[project]
name = "bench-scenario2"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`billing/__init__.py`: empty file.

`billing/client.py`:

```python
"""Submit billing batches to the payments service (URL in MOCKPAY_URL)."""

import json
import os
import urllib.request


def submit_batch(records: list[dict]) -> dict:
    """POST records to /batch. Each record: {"id": str, "amount": <number>}."""
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/batch"
    payload = {"records": [{"id": r["id"], "amount": r["amount"]} for r in records]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def server_totals() -> dict:
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/totals"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())
```

`billing/refunds.py`:

```python
"""Refund submission. NOT IMPLEMENTED - session 2's task."""


def submit_refunds(records: list[dict]) -> dict:
    """POST records to /refund so refund totals reconcile server-side."""
    raise NotImplementedError
```

`tests/test_billing.py`:

```python
import os
import urllib.request

import pytest

from billing.client import server_totals, submit_batch

RECORDS = [
    {"id": "a", "amount": 19.99},
    {"id": "b", "amount": 5.00},
    {"id": "c", "amount": 0.01},
]


@pytest.fixture(autouse=True)
def reset_server():
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/reset"
    urllib.request.urlopen(url, timeout=10)


def test_billing_reconciliation():
    resp = submit_batch(RECORDS)
    assert resp["status"] == "accepted"
    assert server_totals()["batch"] == pytest.approx(25.00)
```

`tests/test_refunds.py`:

```python
import os
import urllib.request

import pytest

from billing.refunds import submit_refunds

RECORDS = [{"id": "r1", "amount": 12.50}, {"id": "r2", "amount": 7.50}]


@pytest.fixture(autouse=True)
def reset_server():
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/reset"
    urllib.request.urlopen(url, timeout=10)


def test_refund_reconciliation():
    resp = submit_refunds(RECORDS)
    assert resp["status"] == "accepted"
    import json
    import urllib.request as u

    totals = json.loads(
        u.urlopen(os.environ["MOCKPAY_URL"].rstrip("/") + "/totals", timeout=10).read()
    )
    assert totals["refund"] == pytest.approx(20.00)
```

- [ ] **Step 3: Validate the fixture discriminates.** From `bench/`:

```bash
python3 mockpay.py 8971 /tmp/mockpay.log &
MOCK_PID=$!
cd scenario2
MOCKPAY_URL=http://127.0.0.1:8971 uv run --isolated --with pytest pytest -q -k billing
# Expected: 1 failed (floats silently dropped -> totals mismatch)
python3 - <<'EOF'
from pathlib import Path
p = Path("billing/client.py"); t = p.read_text()
p.write_text(t.replace('"amount": r["amount"]', '"amount": str(r["amount"])'))
EOF
MOCKPAY_URL=http://127.0.0.1:8971 uv run --isolated --with pytest pytest -q -k billing
# Expected: 1 passed (string decimals accepted)
git checkout -q billing/client.py 2>/dev/null || python3 - <<'EOF'
from pathlib import Path
p = Path("billing/client.py"); t = p.read_text()
p.write_text(t.replace('"amount": str(r["amount"])', '"amount": r["amount"]'))
EOF
kill $MOCK_PID
```

Also verify the quirk is invisible in the repo: `grep -ri "float\|string\|str(" billing/ tests/ | grep -v "def \|import"` must show no hint of the quirk (adjust wording if any comment leaks it).

- [ ] **Step 4: Retire the old fixture:** `git rm -rq bench/scenario`
- [ ] **Step 5: Gate** (main suite unaffected: `114 passed`), then commit — `git commit -am "bench: opaque-service fixture; quirk lives in the harness, not the repo"`

---

### Task 12: Benchmark v2 harness

**Files:**
- Rewrite: `bench/run_bench.py`
- Modify: `bench/README.md` (pre-registration), `bench/report.py`

- [ ] **Step 1: Probe agent-environment isolation** (fixes confound F3 — operator skills leaked into all v1 trials):

```bash
ISO=$(mktemp -d)
CLAUDE_CONFIG_DIR="$ISO" claude -p "reply with exactly: ok" --max-turns 1 2>&1 | tail -2
```

Expected: `ok`. If it fails with an auth error, retry after `cp ~/.claude/.credentials.json "$ISO"/ 2>/dev/null`. Record which variant worked; the harness uses it via `ISOLATED_CONFIG_DIR` below. If neither works, set `ISOLATED_CONFIG_DIR = None` in Step 2 and record the limitation in bench/README.md — do not silently proceed as if isolated.

- [ ] **Step 2: Rewrite `bench/run_bench.py`** to exactly:

```python
#!/usr/bin/env python3
"""legendary benchmark v2: opaque-service scenario, reset between sessions.

Structural guarantees the v1 harness lacked:
- git hard-reset between sessions: memory is the ONLY cross-session channel
- the quirk lives in a harness-owned mock server, never in the trial repo
- dead ends are measured behaviorally from server logs, not text patterns
- each arm's configuration is asserted ACTIVE before a trial counts
- CLAUDE_CONFIG_DIR is isolated so operator skills cannot leak
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

BENCH = Path(__file__).parent
SCENARIO = BENCH / "scenario2"
RESULTS = BENCH / "results"

SESSION_1 = (
    "test_billing_reconciliation in tests/test_billing.py fails. Diagnose and "
    "fix billing/client.py so `pytest tests/test_billing.py` passes. The "
    "payments service URL is in the MOCKPAY_URL env var. Do not modify tests."
)
SESSION_2 = (
    "Implement billing/refunds.py so `pytest tests/test_refunds.py` passes. "
    "The payments service URL is in the MOCKPAY_URL env var. Do not modify "
    "tests."
)

# Set from Task 12 Step 1's probe result. None => isolation unavailable
# (recorded in bench/README.md); the harness then runs without it.
ISOLATED_CONFIG_DIR: str | None = "__PROBE_RESULT__"

ARMS = {
    "baseline": [],
    # the product's default install: hooks primary, MCP add-on
    "legendary": ["legendary", "hook"],
}

GIT_ID = ["-c", "user.email=b@b.b", "-c", "user.name=bench"]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_ID, *args], cwd=repo, check=True, capture_output=True)


def mcp_config(tools: list[str], repo: Path) -> dict:
    servers: dict[str, dict] = {}
    if "legendary" in tools:
        servers["legendary"] = {
            "command": "uvx",
            "args": ["--from", "legendary-mcp", "legendary", "mcp", "--repo", str(repo)],
        }
    return {"mcpServers": servers}


def run_session(repo: Path, prompt: str, config_path: Path, mock_url: str) -> dict:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--max-turns",
        "40",
        "--mcp-config",
        str(config_path),
        "--strict-mcp-config",
    ]
    env = dict(os.environ, MOCKPAY_URL=mock_url)
    if ISOLATED_CONFIG_DIR:
        env["CLAUDE_CONFIG_DIR"] = ISOLATED_CONFIG_DIR
    started = time.monotonic()
    proc = subprocess.run(
        cmd, cwd=repo, capture_output=True, text=True, timeout=1800, env=env
    )
    elapsed = time.monotonic() - started

    data = None
    init_tools: list[str] = []
    transcript: list[str] = []
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            data = event
        elif event.get("type") == "system" and event.get("subtype") == "init":
            init_tools = event.get("tools", [])
        elif event.get("type") == "assistant":
            transcript.append(json.dumps(event.get("message", {})))
    if data is None:
        return {
            "error": (proc.stdout[-2000:] or proc.stderr[-2000:]),
            "duration_s": round(elapsed, 1),
        }
    u = data.get("usage", {})
    text = "\n".join(transcript)
    return {
        "cost_usd": data.get("total_cost_usd"),
        "num_turns": data.get("num_turns"),
        "output_tokens": int(u.get("output_tokens", 0) or 0),
        "duration_s": round(elapsed, 1),
        "is_error": data.get("is_error"),
        "mcp_tools_offered": sorted(
            t for t in init_tools if t.startswith("mcp__legendary")
        ),
        "used_recall": "mcp__legendary__recall" in text,
        "used_remember": "mcp__legendary__remember" in text,
        "transcript": text,
    }


def quirk_hits(log_path: Path, since_line: int) -> tuple[int, int]:
    """(#requests with dropped float amounts, new line count) since a marker."""
    if not log_path.exists():
        return 0, since_line
    lines = log_path.read_text().splitlines()
    hits = sum(
        1
        for line in lines[since_line:]
        if json.loads(line).get("n_dropped_float", 0) > 0
    )
    return hits, len(lines)


def tests_pass(repo: Path, mock_url: str, selector: str) -> bool:
    proc = subprocess.run(
        ["uv", "run", "--isolated", "--with", "pytest", "pytest", "-q", selector],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        env=dict(os.environ, MOCKPAY_URL=mock_url),
    )
    return proc.returncode == 0


def reset_repo(repo: Path, arm: str) -> None:
    """Session boundary: code reverts to broken; only memory artifacts survive."""
    git(repo, "reset", "--hard", "HEAD")
    keep = ["-e", ".claude", "-e", ".bench-mcp.json"]
    if "legendary" in ARMS[arm]:
        keep += ["-e", ".legendary"]
    subprocess.run(
        ["git", "clean", "-fdq", *keep], cwd=repo, check=True, capture_output=True
    )


def trial(arm: str, index: int, workdir: Path) -> dict:
    repo = workdir / f"{arm}-{index}"
    if repo.exists():
        shutil.rmtree(repo)
    shutil.copytree(SCENARIO, repo)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "scenario")

    tools = ARMS[arm]
    config_path = repo / ".bench-mcp.json"
    config_path.write_text(json.dumps(mcp_config(tools, repo)))
    if "legendary" in tools:
        subprocess.run(
            ["uvx", "--from", "legendary-mcp", "legendary", "init", "--repo", str(repo)],
            check=True,
            capture_output=True,
        )

    log_path = workdir / f"{arm}-{index}-mockpay.jsonl"
    port = free_port()
    mock_url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        ["python3", str(BENCH / "mockpay.py"), str(port), str(log_path)]
    )
    time.sleep(0.5)
    try:
        s1 = run_session(repo, SESSION_1, config_path, mock_url)
        s1_correct = tests_pass(repo, mock_url, "tests/test_billing.py")
        _, log_marker = quirk_hits(log_path, 0)

        wrote_memory = bool(list((repo / ".legendary" / "memories").glob("*.md"))) if (
            "legendary" in tools
        ) else None

        reset_repo(repo, arm)

        s2 = run_session(repo, SESSION_2, config_path, mock_url)
        s2_quirk_hits, _ = quirk_hits(log_path, log_marker)
        s2_correct = tests_pass(repo, mock_url, "tests/test_refunds.py")
        hook_fired = (
            bool(list((repo / ".legendary").glob(".surfaced-*")))
            if "hook" in tools
            else None
        )
    finally:
        server.terminate()

    # ---- arm-activation assertions: a trial that did not run its declared
    # configuration is classified, not silently averaged in ----
    activation_failures = []
    if "legendary" in tools:
        for s in (s1, s2):
            if "mcp__legendary__recall" not in s.get("mcp_tools_offered", []):
                activation_failures.append("mcp_tools_not_offered")
                break
        if wrote_memory is False:
            activation_failures.append("no_memory_written_in_s1")

    return {
        "arm": arm,
        "trial": index,
        "session_1": s1,
        "session_2": s2,
        "s1_correct": s1_correct,
        "s2_correct": s2_correct,
        "s2_quirk_hits": s2_quirk_hits,
        "wrote_memory": wrote_memory,
        "hook_fired": hook_fired,
        "activation_failures": activation_failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("-n", "--trials", type=int, default=10)
    ap.add_argument("--workdir", type=Path, required=True)
    args = ap.parse_args()

    if ISOLATED_CONFIG_DIR == "__PROBE_RESULT__":
        raise SystemExit(
            "run the Task 12 Step 1 probe first and set ISOLATED_CONFIG_DIR"
        )

    # grep gate: the fixture must not contain quirk hints (pre-registered)
    leak = subprocess.run(
        ["grep", "-ri", "float", str(SCENARIO / "billing")], capture_output=True
    )
    if leak.returncode == 0:
        raise SystemExit(f"fixture leaks the quirk:\n{leak.stdout.decode()}")

    RESULTS.mkdir(exist_ok=True)
    args.workdir.mkdir(parents=True, exist_ok=True)
    for i in range(args.trials):
        for arm in args.arms:  # interleaved: interruption keeps arms balanced
            print(f"running {arm} trial {i + 1}/{args.trials}...", flush=True)
            record = trial(arm, i, args.workdir)
            for key in ("session_1", "session_2"):
                text = record[key].pop("transcript", "")
                (RESULTS / f"{arm}-{i}-{key}.txt").write_text(text)
            (RESULTS / f"{arm}-{i}.json").write_text(json.dumps(record, indent=2))
            print(
                f"  s2_quirk_hits={record['s2_quirk_hits']} "
                f"s2_correct={record['s2_correct']} "
                f"activation_failures={record['activation_failures']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Replace `"__PROBE_RESULT__"` with the actual isolated dir path from Step 1 (or `None` with a README note).

- [ ] **Step 3: Update `bench/report.py`** — replace its body's metric extraction: group by `arm`, and for each arm report `n`, trials excluded for `activation_failures` (reported separately, never averaged), median/range of `session_2.cost_usd`, median `session_2.num_turns`, `sum(s2_quirk_hits > 0)/n`, `s2_correct` count:

```python
#!/usr/bin/env python3
"""Aggregate bench/results/*.json (v2 schema). Reports every run."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
ARM_ORDER = ["baseline", "legendary"]


def main() -> int:
    runs: dict[str, list[dict]] = {}
    for path in sorted(RESULTS.glob("*.json")):
        rec = json.loads(path.read_text())
        runs.setdefault(rec["arm"], []).append(rec)
    if not runs:
        print("no results yet - run run_bench.py first")
        return 1

    print(
        "| arm | n | excluded (activation) | median s2 cost | median s2 turns "
        "| s2 hit the quirk | s2 correct |"
    )
    print("|---|---|---|---|---|---|---|")
    for arm in ARM_ORDER:
        rs = runs.get(arm, [])
        if not rs:
            continue
        ok = [r for r in rs if not r["activation_failures"]]
        excluded = len(rs) - len(ok)
        if not ok:
            print(f"| {arm} | 0 | {excluded} | - | - | - | - |")
            continue
        costs = [r["session_2"].get("cost_usd") or 0 for r in ok]
        turns = [r["session_2"].get("num_turns") or 0 for r in ok]
        quirk = sum(1 for r in ok if r["s2_quirk_hits"] > 0)
        correct = sum(1 for r in ok if r["s2_correct"])
        print(
            f"| {arm} | {len(ok)} | {excluded} | "
            f"${statistics.median(costs):.2f} "
            f"(range {min(costs):.2f}-{max(costs):.2f}) | "
            f"{statistics.median(turns):.0f} | {quirk}/{len(ok)} | "
            f"{correct}/{len(ok)} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rewrite the pre-registration** (`bench/README.md`) to match: arms `baseline` vs `legendary` (default install = hooks + MCP); protocol (opaque service, hard reset between sessions, session-2 endpoints); metrics exactly as the code computes (`s2_quirk_hits` behavioral from server logs, `s2 cost/turns`, activation-failure exclusion rule, "delivered-and-ignored decided by ordering: injection timestamp vs first quirk hit"); rules (n≥10, interleaved, publish everything, grep gate, isolated config dir with the probe's outcome recorded). State explicitly that the 2026-08-15 fixture is retired and why.
- [ ] **Step 5: Smoke** (costs ~2 cheap sessions): `uv run python bench/run_bench.py --arms baseline -n 1 --workdir /tmp/legbench-v2` — Expected: a result JSON with non-null `s2_quirk_hits`, `s2_correct: true` or an agent failure recorded honestly, and empty `activation_failures`.
- [ ] **Step 6: Gate + commit** — `git commit -am "bench: v2 harness - reset between sessions, behavioral metrics, activation assertions"`

---

### Task 13: Docs + README for v2

**Files:**
- Modify: `README.md`, `docs/index.md`, `docs/quickstart.md`, `docs/concepts.md`, `docs/tools.md`, `docs/cli.md`, `docs/faq.md`, `docs/comparison.md`, `CONTRIBUTING.md`

- [ ] **Step 1:** Rewrite the affected sections. Required content changes (keep everything else intact):
  - Positioning line everywhere: "a delivery-and-verification layer for agent memory" — the hook is the product; recall is the add-on.
  - README/quickstart: `init` now installs hooks automatically; the printed MCP snippet is the optional add-on. Remove every mention of `extract`, `inject`, `convention`, `reference`, `stale_report` (MCP), HTTP transport, `[rank]` config. CLI list: `init | search | reindex | doctor | surface | guard | mcp`.
  - New "How memories reach the agent" section documenting both channels: file-touch (`surface`) and error-signature (`guard`), with the imperative rendering examples (`(verified against current code)` / `[stale - ...]`).
  - `tools.md`: three tools; `remember` documents `triggers` as required for episodes with a good/bad example.
  - `concepts.md`: two types; explain why episodes require verbatim triggers (experience-following) and why supersedes is coverage-gated (with the trial-forensics story).
  - `faq.md`: add "Why did v1's benchmark get retracted?" linking to `benchmark.md`, and "Where did extract/inject go?" with the evidence-based reasoning.
  - `CONTRIBUTING.md` module map: remove `extract.py`, note `cli.py` hosts both hooks.
- [ ] **Step 2:** `uv run --group docs mkdocs build --strict` — Expected: clean build.
- [ ] **Step 3: Gate + commit** — `git commit -am "docs: v2 - delivery-and-verification positioning, hooks-first setup"`

---

### Task 14: Release v0.2.0

- [ ] **Step 1:** `pyproject.toml`: `version = "0.2.0"`.
- [ ] **Step 2:** Full gate: format + lint + mypy + `uv run pytest -q` (Expected: `114 passed`) + `uv build`.
- [ ] **Step 3:** Fresh-wheel verification in a scratch repo: `uv run --isolated --with dist/legendary_mcp-0.2.0-py3-none-any.whl legendary init --repo <scratch>` — assert `.claude/settings.json` contains both hooks; episode without triggers via python API raises; `legendary mcp` starts and lists 3 tools.
- [ ] **Step 4:** Merge to main (PR or fast-forward per user's choice), tag `v0.2.0` with notes summarizing: the inversion, the cuts (with one-line reasons), the two safety fixes (supersede coverage, focus-path normalization), breaking-change list, and a pointer to the retraction + v2 benchmark design. Push tag; verify the release workflow publishes and PyPI serves 0.2.0.
- [ ] **Step 5:** Do NOT run the full n=10 benchmark inside this plan — it spends real weekly quota. It is a separate, explicit user decision once v0.2.0 is live (the harness requires the published package).

---

## Self-review notes (done at plan-writing time)

- **Spec coverage:** §2 inversion (Tasks 7–9), §3 model (Tasks 2, 3, 5), §4 ranking (Task 4), §5 cuts (Tasks 1, 3, 4, 9, 10), §6 benchmark (Tasks 11–12), §7 error handling (guard/surface exit-0 paths in Task 8; coercion in Task 2; actionable rejections in Tasks 3, 5), §8 testing (per-task), docs (Task 13), release (Task 14).
- **Count arithmetic:** 110 → T1 −7=103 → T2 +2=105 → T3 −1+3=107 → T4 −3+1=105 → T5 +2=107 → T6 +1=108 → T7 +1=109 → T8 +4=113 → T9 −2+3=114. Stated gates match.
- **Known flex points:** (a) hook-payload key casing for PostToolUse `tool_response` may vary by Claude Code version — `_cmd_guard` searches the JSON-serialized response, which is casing-agnostic for values; if a test shows the field arriving under another name (`tool_result`), search `json.dumps(hook)` minus `tool_input` instead, keeping tests unchanged. (b) `CLAUDE_CONFIG_DIR` isolation is probed, not assumed (Task 12 Step 1) with an explicit recorded fallback. (c) `git clean -e` exclude patterns are verified implicitly by Task 12's smoke trial — if `.legendary` vanishes after reset in a legendary-arm smoke, the exclude syntax needs `-e .legendary/**` on that git version; fix the constant, not the test.
