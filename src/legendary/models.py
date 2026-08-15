"""Core data models: Anchor and Memory, with markdown (de)serialization."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

MemoryType = Literal["decision", "episode", "convention", "reference"]
MemorySource = Literal["agent", "auto-extract", "human"]
MemoryStatus = Literal["active", "deprecated"]

FRONTMATTER_SEP = "---"


class Anchor(BaseModel):
    file: str
    symbol: Optional[str] = None
    lines: Optional[tuple[int, int]] = None  # 1-based inclusive
    commit: Optional[str] = None
    content_hash: Optional[str] = None


class Memory(BaseModel):
    id: str
    type: MemoryType
    title: str
    body: str
    created: datetime
    source: MemorySource = "agent"
    status: MemoryStatus = "active"
    deprecated_reason: Optional[str] = None
    superseded_by: Optional[str] = None
    transcript: Optional[str] = None
    anchors: list[Anchor] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @staticmethod
    def new_id(title: str, created: datetime) -> str:
        digest = hashlib.sha256(f"{title}{created.isoformat()}".encode()).hexdigest()
        return f"mem-{digest[:8]}"

    def to_markdown(self) -> str:
        meta = self.model_dump(exclude={"body"}, exclude_none=True, mode="json")
        front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
        return f"{FRONTMATTER_SEP}\n{front}\n{FRONTMATTER_SEP}\n{self.body}\n"

    @classmethod
    def from_markdown(cls, text: str) -> "Memory":
        # The delimiter scan is anchored to line boundaries: a bare substring
        # search would treat any "---" at the end of a frontmatter value (a
        # title, tag, or deprecation reason) as the closing delimiter.
        opening = f"{FRONTMATTER_SEP}\n"
        if not text.startswith(opening):
            raise ValueError("not a frontmatter markdown memory")
        rest = text[len(opening) :]
        end = rest.find(f"\n{FRONTMATTER_SEP}\n")
        if end == -1:
            raise ValueError("unterminated frontmatter in markdown memory")
        meta = yaml.safe_load(rest[:end])
        if not isinstance(meta, dict):
            raise ValueError("frontmatter is not a mapping")
        meta.pop("body", None)
        body = rest[end + len(FRONTMATTER_SEP) + 2 :].rstrip("\n")
        return cls(body=body, **meta)
