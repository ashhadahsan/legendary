# FAQ

**Does my code get sent anywhere?**
No. Anchoring, hashing, indexing, retrieval, and both hooks are entirely local.
v0.2 removed the one feature that called an LLM.

**Do I need an API key or a vector database?**
No and no. Retrieval is SQLite FTS5 plus anchor and trigger matching.

**Where did `extract` and `inject` go?**
Deleted in v0.2. `extract` was an LLM pass over session transcripts — write-side
sophistication that the evidence says buys 3-8 points where retrieval buys 20,
and its fallback path silently saved unanchored, unverifiable memories.
`inject` dumped memories at session start, the point of maximum context
dilution; it was never once referenced in our benchmark transcripts.

**Where did `convention` and `reference` types go?**
Also deleted. CLAUDE.md and your docs already hold that knowledge, and hosts
inject CLAUDE.md for free. Memories written under those types in v0.1 load as
`decision`.

**Why does an episode need triggers?**
Because otherwise it can never be pushed — only searched, which is the weakest
channel. The trigger is what lets the memory resurface at the moment the same
failure happens again.

**Should memories be committed to git?**
Yes. That is the team-sharing mechanism: your teammate clones the repo and
their agent immediately has your failed attempts. The index is gitignored and
rebuilds itself.

**Why return stale memories at all instead of hiding them?**
Because the reasoning usually outlives the code. Hiding it loses knowledge;
flagging it lets the agent judge.

**Does it work with Gemini CLI, Cursor, Codex, or other agents?**
Partly, and the difference matters. The MCP tools (`remember`, `recall`,
`deprecate`) work in any MCP host, Gemini CLI included. The **hooks do not** -
`surface` and `guard` are wired through Claude Code's `PreToolUse`/`PostToolUse`
settings format, which is Claude Code specific.

Since v0.2 the hooks are the primary channel, that is a real limitation rather
than a footnote: on non-Claude-Code hosts you get agent-initiated search only,
which is the weaker half of the product. Both `surface` and `guard` are plain
CLI commands that read hook JSON on stdin and print JSON out, so any host with
an equivalent hook mechanism can drive them - but we have only tested Claude
Code, and we will not claim otherwise until we have.

**What languages support symbol anchoring?**
Python, JavaScript, TypeScript, TSX. Line-range and whole-file anchoring work
for any language, and unsupported files degrade gracefully rather than failing.

**Does legendary make my agent faster or cheaper?**
Unproven, and we will not claim it until a valid benchmark says so. Our first
attempt was retracted for measuring nothing — see [benchmark](benchmark.md).

**Is it production-ready?**
v0.2 is a breaking redesign of a young tool. The core — anchoring, staleness,
push delivery — is tested and works. Expect the API to keep moving.
