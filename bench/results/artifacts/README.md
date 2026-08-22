# Preserved trial artifacts

Evidence for the benchmark results and for two retractions. Copied out of
`/tmp` (ephemeral) on 2026-08-21.

Per trial repo, where present:

- `.legendary/memories/*.md` — what the agent actually stored
- `.legendary/.surfaced-*`, `.guarded-*` — hook delivery caches
- `.claude/settings.json` — which hooks were actually installed
- `.bench-mcp.json` — which MCP servers the arm actually had
- `*-mockpay.jsonl` — the mock server's request log (the behavioral metric)

These files are what showed the ablation was invalid: `hooks_only` repos have
no `memories/` at all (no write channel, and `git clean` removed the store),
while `recall_only` repos contain legendary hooks in `.claude/settings.json`
and `.surfaced-*` caches — proving that arm was not hook-free.
