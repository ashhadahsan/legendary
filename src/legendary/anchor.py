"""Resolve an Anchor to source text, normalize it, and hash it."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Optional

from legendary.models import Anchor

# file suffix -> tree-sitter language name
_LANGS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}
_DEF_TYPES = {
    "python": {"function_definition", "class_definition"},
    "javascript": {"function_declaration", "class_declaration", "method_definition"},
    "typescript": {"function_declaration", "class_declaration", "method_definition"},
    "tsx": {"function_declaration", "class_declaration", "method_definition"},
}


def normalize(text: str) -> str:
    """Whitespace-insensitive form: strip each line, drop blank lines."""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def hash_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(normalize(text).encode()).hexdigest()


def _find_def(node: Any, name: str, def_types: set[str]) -> Any:
    for child in node.children:
        if child.type in def_types:
            n = child.child_by_field_name("name")
            if n is not None and n.text.decode() == name:
                return child
        found = _find_def(child, name, def_types)
        if found is not None:
            return found
    return None


def _symbol_span(path: Path, symbol: str) -> Optional[tuple[int, int]]:
    """Return 1-based inclusive (start, end) lines of a possibly dotted symbol."""
    lang = _LANGS.get(path.suffix)
    if lang is None:
        return None
    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(lang)
    except Exception:
        return None
    tree = parser.parse(path.read_bytes())
    scope = tree.root_node
    for part in symbol.split("."):
        scope = _find_def(scope, part, _DEF_TYPES[lang])
        if scope is None:
            return None
    return (scope.start_point[0] + 1, scope.end_point[0] + 1)


def region_text(repo_root: Path, anchor: Anchor) -> Optional[tuple[str, tuple[int, int]]]:
    """Resolve anchor to (text, (start_line, end_line)). None if file is gone.

    Resolution order: symbol -> lines -> whole file. An unresolvable symbol
    falls back to lines (if present) then whole file.
    """
    path = repo_root / anchor.file
    if not path.is_file():
        return None
    all_lines = path.read_text(errors="replace").splitlines()

    if anchor.symbol:
        span = _symbol_span(path, anchor.symbol)
        if span is not None:
            s, e = span
            return "\n".join(all_lines[s - 1 : e]), (s, e)
    if anchor.lines:
        s, e = anchor.lines
        s = max(1, s)
        e = min(len(all_lines), e)
        # If the range clamps to empty (the file shrank), fall through to the
        # whole-file branch. None is reserved strictly for a missing file.
        if s <= e:
            return "\n".join(all_lines[s - 1 : e]), (s, e)
    return "\n".join(all_lines), (1, max(1, len(all_lines)))


def _head_commit(repo_root: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def resolve_and_hash(repo_root: Path, anchor: Anchor) -> Anchor:
    """Fill lines, commit, and content_hash at write time.

    Strict on the WRITE path (spec 3.2): the file must exist and a given symbol
    must resolve, so the agent gets an actionable rejection instead of a silent
    whole-file anchor. region_text stays lenient for recall-time re-resolution.
    """
    path = repo_root / anchor.file
    if anchor.symbol and path.is_file() and _symbol_span(path, anchor.symbol) is None:
        raise ValueError(
            f"symbol {anchor.symbol!r} not found in {anchor.file} - "
            "retry with a line range (lines: [start, end]) or drop the symbol"
        )
    resolved = region_text(repo_root, anchor)
    if resolved is None:
        raise FileNotFoundError(f"anchor file not found: {anchor.file}")
    text, lines = resolved
    return anchor.model_copy(
        update={
            "lines": lines,
            "commit": _head_commit(repo_root),
            "content_hash": hash_text(text),
        }
    )
