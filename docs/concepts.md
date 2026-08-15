# Concepts

## Anchors

An anchor binds a memory to code:

```yaml
anchors:
  - file: src/sync/worker.py
    symbol: SyncWorker.run
    lines: [120, 164]
    commit: 8fa2c31
    content_hash: sha256:9f8e...
```

At write time legendary resolves the symbol with tree-sitter (Python, JS, TS,
TSX), records the span and the current commit, and hashes the region.

Write-time validation is strict: if you name a symbol that does not exist, the
call is rejected with an actionable message rather than silently anchoring to
the whole file.

## Staleness verdicts

Computed **at recall time** - there is no daemon and no watcher.

| Verdict | Meaning |
|---|---|
| `fresh` | the anchored region hashes the same as when written |
| `stale` | the region changed - the memory may be out of date |
| `orphaned` | the file or symbol is gone entirely |

Two deliberate non-triggers: whitespace-only edits do not invalidate a memory
(the hash is over a normalized form), and a symbol that merely *moves* stays
`fresh`, because anchors are re-resolved by symbol before hashing.

Stale memories are still returned, ranked lower and clearly flagged. The *why*
behind a decision often survives the refactor that invalidated its anchor.

## Memory types

| Type | Use for |
|---|---|
| `decision` | why the code is the way it is |
| `episode` | an approach that was tried and **failed**, and why |
| `convention` | a project or team practice |
| `reference` | an authoritative external doc or ticket |

`episode` is the highest-value type and the one no other system stores. It is
what stops an agent from re-running a fix that already failed.

## Storage

The canonical store is one markdown file per memory in
`.legendary/memories/`, committed to your repo. `index.db` is a derived SQLite
FTS5 index; it is gitignored and rebuilt automatically when missing or corrupt,
so a fresh clone works with no setup.

Because ids are content-derived rather than sequential, two teammates adding
memories on separate branches merge cleanly.
