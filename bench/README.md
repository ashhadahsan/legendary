# legendary benchmark

Pre-registered **before** any run, and committed, so results cannot be
retro-fitted to a conclusion.

## Question

Does code-anchored memory reduce tokens-to-completion and prevent repeated
failed approaches on multi-session tasks?

## Arms (identical except MCP configuration)

1. `baseline` - no memory, no graph tooling
2. `graphify` - Graphify MCP only
3. `legendary` - legendary MCP only
4. `both` - Graphify + legendary

`graphify` is included because it is the closest well-known tool in the space,
and because the honest hypothesis is that the two are **complementary** rather
than competing: Graphify models code structure, legendary remembers decisions
and failures. If `both` wins, that is the result we publish.

## Protocol

Each trial is TWO sessions with separate context - the amnesia boundary is the
thing under test:

- **Session 1:** fix the failing concurrency test for `sync/worker.py`. The
  counter is incremented with a read-modify-write inside a *deferred*
  transaction. Under concurrency SQLite returns `SQLITE_BUSY` on the lock
  upgrade **without invoking the busy handler**, because retrying cannot
  resolve it. So the two most intuitive fixes - raising `busy_timeout` and
  wrapping in `BEGIN TRANSACTION` - are genuine dead ends. Only
  `BEGIN IMMEDIATE` works.
- **Session 2 (fresh context):** fix the same class of bug in
  `sync/reporter.py`. Without memory of session 1, agents re-explore the same
  dead ends.

Fixture validated four ways before benchmarking:

| attempt | result |
|---|---|
| broken baseline | fails |
| larger `busy_timeout` (60s) | still fails |
| `BEGIN TRANSACTION` (deferred) | still fails |
| `BEGIN IMMEDIATE` | passes |

The previous fixture was discarded: it allowed a legitimate
`sqlite3.connect(timeout=...)` fix, so no agent was tempted into the trap and
`repeated_failure` could not discriminate. That run stays in git history.

## Pre-registered metrics

- `tokens_total` = input + cache_creation + cache_read + output, both sessions
- `cost_usd`, `duration_s`, `num_turns`
- `dead_ends` (per session) - which of `DEAD_END_PATTERNS` in run_bench.py
  appear in that session's assistant transcript: `busy_timeout`,
  `BUSY_TIMEOUT_MS`, `timeout=`, `time.sleep`, `BEGIN TRANSACTION`,
  `BEGIN DEFERRED`. This list and the code must stay identical.
- `repeated_failure` (bool) - true when session 2 explored any dead end.
  Measured from session 2's **transcript**, not the final diff: an agent that
  tries `busy_timeout`, watches it fail, and reverts it leaves no diff trace
  but has still burned the tokens.
- `found_correct_fix` (bool) - `BEGIN IMMEDIATE` appears in the transcript
- `correct` (bool) - does `pytest` pass in the scenario repo afterwards?

## Rules

- N >= 5 trials per arm; report median and full range, never a single run.
- Identical prompts across arms; prompts are fixed in `run_bench.py` and
  committed.
- Every arm runs with `--strict-mcp-config`, including `baseline` (with an
  empty server map), so no arm inherits ambient MCP servers.
- ALL runs are published in `bench/results/*.json`, including failures and runs
  where legendary loses. No run is discarded after the fact.
- Author bias disclosed: we wrote legendary. Anyone can re-run this.

## Running it

```bash
uv run python bench/run_bench.py --arms baseline -n 1 --workdir /tmp/legbench  # smoke
uv run python bench/run_bench.py -n 5 --workdir /tmp/legbench                  # full
uv run python bench/report.py
```

This costs real API credits (4 arms x 5 trials x 2 sessions = 40 agent
sessions). It is deliberately not run in CI.
