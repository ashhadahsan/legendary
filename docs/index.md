# legendary

**Code-anchored, staleness-aware, git-native memory for coding agents.**

Coding agents are stateless. Every session re-reads your repo, re-derives
decisions you already made, and retries fixes that already failed. Memory
frameworks remember conversations but are code-blind: a memory never knows it
was about `src/sync/worker.py:120`, and never notices when that code changes.

legendary merges the two sides.

## The one thing nothing else does

```console
$ legendary search "strip None"
strip() breaks on None   [fresh]

$ vim app.py     # edit the anchored function

$ legendary search "strip None"
strip() breaks on None   [stale - parse changed since 8fa2c31]
```

Every other memory system would still hand you that memory with full
confidence. Stale memory is worse than no memory: the agent acts on a claim
that stopped being true weeks ago.

## Properties

- **Anchored** - each memory links to a file / symbol / line range at a commit
- **Staleness-aware** - anchored code changes, the memory says so
- **Typed** - `decision`, `episode` (tried X, failed because Y), `convention`,
  `reference`
- **Git-native** - markdown in `.legendary/memories/`, committed with your
  code, reviewed in PRs, shared by the whole team
- **Local-first** - no cloud, no accounts, no API keys, no embeddings

Start with the [Quickstart](quickstart.md), or browse the
[source on GitHub](https://github.com/ashhadahsan/legendary).
