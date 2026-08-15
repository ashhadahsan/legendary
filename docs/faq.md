# FAQ

**Does my code get sent anywhere?**
No. Anchoring, hashing, indexing, and retrieval are entirely local. The only
feature that calls an LLM is the optional `legendary extract`, which runs your
own local `claude` CLI.

**Do I need an API key?**
No.

**Do I need a vector database or embeddings?**
No. Retrieval is SQLite FTS5 plus anchor matching. This keeps recall
deterministic and instant, and keeps install to a single command. Optional
local embeddings are on the roadmap, not a requirement.

**Should memories be committed to git?**
Yes - that is the team-sharing mechanism. Your teammate clones the repo and
their agent immediately has your decisions and failed attempts. The index
(`index.db`) is gitignored and rebuilds itself.

**What happens on merge conflicts?**
Rarely an issue: one file per memory, and ids are content-derived rather than
sequential, so two people adding memories on separate branches do not collide.

**Why return stale memories at all instead of hiding them?**
Because the reasoning usually outlives the code. "We chose X because Y" stays
useful after a refactor moves the code. Hiding it loses knowledge; flagging it
lets the agent judge.

**What languages are supported for symbol anchoring?**
Python, JavaScript, TypeScript, and TSX. Anchoring by line range or whole file
works for any language, and unsupported files degrade gracefully.

**How is this different from just writing things in CLAUDE.md?**
CLAUDE.md is unstructured, unsearchable, loaded in full every session, and has
no idea when its claims stop being true. legendary is searchable, ranked,
surfaced only when relevant, and self-invalidating.

**Is it production-ready?**
It is v1. The core (anchoring, staleness, recall, MCP, CLI) is tested and
working. Expect the roadmap items - richer extraction, more languages, import-
graph reranking - to land incrementally.
