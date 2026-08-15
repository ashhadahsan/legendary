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

- **Session 1:** fix the failing concurrency test for `sync/worker.py`. A
  plausible-looking fix (wrapping the writes in an explicit
  `BEGIN TRANSACTION`) does **not** work; the working fix is
  `PRAGMA busy_timeout`. The agent discovers this the hard way.
- **Session 2 (fresh context):** fix the same class of bug in
  `sync/reporter.py`. An agent with no memory of session 1 tends to retry the
  transaction approach.

The fixture is validated: broken -> both tests fail; `busy_timeout` -> both
pass; `BEGIN TRANSACTION` -> still fails.

## Pre-registered metrics

- `tokens_total` = input + cache_creation + cache_read + output, both sessions
- `cost_usd`, `duration_s`, `num_turns`
- `repeated_failure` (bool) - did session 2 introduce the known-bad pattern?
  Detected deterministically by searching session 2's diff (case-insensitive)
  for any pattern in `BAD_PATTERNS` in `run_bench.py`, which is exactly
  `BEGIN TRANSACTION` and `conn.execute("BEGIN`. This list and the code must
  stay identical; changing one without the other invalidates the results.
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
