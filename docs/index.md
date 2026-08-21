# legendary

**A delivery-and-verification layer for coding-agent memory.**

Most knowledge already has a home: decisions belong in comments and ADRs,
conventions in CLAUDE.md, references in docs. Two things have no home anywhere:

1. **Negative knowledge** — the approach you tried that failed, and why.
   Nobody writes a comment on code that does not exist.
2. **Verification** — CLAUDE.md and conversational memory rot silently. There
   is no mechanism that checks whether a written claim is still true.

legendary does exactly those two things, and pushes the result back at the
moment it matters.

## The mechanism

```console
$ # agent runs tests, sees: AttributeError: 'NoneType' has no attribute 'strip'
This failure has been seen before. Recorded episodes:
- [episode] strip() crashes on None (verified against current code):
  Use a guard: data.strip() if data else "". Retries do not help.
```

No `recall` call. No query. The agent hit a failure whose signature was
recorded, and the episode came back on its own.

Change the anchored code and the same memory arrives differently:

```console
- [episode] strip() crashes on None [stale - code changed since this was
  written; verify before trusting]: ...
```

That downgrade is what makes reusable procedure safe. A stale procedure applied
confidently is worse than no memory at all.

## Properties

- **Pushed, not fetched** — two hooks, installed by `init`
- **Verified** — anchored to file/symbol/commit and content-hashed
- **Local-first** — no cloud, no API keys, no embeddings; SQLite FTS5
- **Git-native** — markdown in your repo, reviewed in PRs, shared by your team

Start with the [Quickstart](quickstart.md), or read
[how memories reach the agent](concepts.md).
