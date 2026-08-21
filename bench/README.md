# legendary benchmark v2

Pre-registered **before** any run, and committed, so results cannot be
retro-fitted to a conclusion.

The v1 benchmark and its n=5 result are **retracted** — see
`docs/benchmark.md`. Its fixture is deleted. This document describes its
replacement, built specifically to make each of v1's four defects structurally
impossible.

## Question

Does pushed, verified memory reduce the cost of a second session on knowledge
that cannot be recovered from the repository?

## Arms

| arm | configuration |
|---|---|
| `baseline` | no memory tooling |
| `legendary` | `legendary init` defaults: both hooks + the MCP add-on |

Both run with `--strict-mcp-config`; `baseline` gets an empty server map so it
cannot inherit ambient MCP servers.

## Protocol

Each trial is two sessions.

- **Session 1:** `test_billing_reconciliation` fails. The payments service
  silently drops any record whose `amount` is a JSON float — and still answers
  `200 {"status": "accepted"}`. The fix is to send string decimals. The service
  is a harness-owned mock (`bench/mockpay.py`) that is **never copied into the
  trial repo**, so the quirk is discoverable only by experiment.
- **Hard reset.** `git reset --hard` + `git clean`, preserving only the arm's
  memory/config artifacts. Session 1's code changes are gone.
- **Session 2:** implement `billing/refunds.py` against a *different* endpoint
  with the same quirk. Baseline must rediscover it; a working memory system
  should not.

The reset is what makes this ungameable: in v1, session 2 could read session 1's
fix in a sibling file, so the task never required memory at all.

### Fixture validation (run before benchmarking)

| attempt | result |
|---|---|
| broken baseline | fails |
| retry / longer timeout | **cannot help** — the server returns `accepted` and no error |
| string decimals | passes |
| grep the repo for the quirk | no match — unrecoverable from code |

## Pre-registered metrics

Primary, both from session 2 only (summing both sessions buries the effect
under session 1's write-time overhead):

- `s2_quirk_hits` — number of session-2 requests containing float amounts,
  counted from the **mock server's own log**. Behavioral, and textually
  unrelated to anything in the repo, so it cannot match source text the way
  v1's detector did.
- `session_2.cost_usd` and `session_2.num_turns`
- `s2_correct` — does `pytest tests/test_refunds.py` pass afterwards

Secondary: `s1_correct`, `wrote_memory`, `hook_fired`, `used_recall`,
`used_remember`.

## Arm-activation assertions

A trial whose configuration did not actually activate is **classified and
excluded**, never silently averaged in. `activation_failures` records:

- `mcp_tools_not_offered` — the init event did not list `mcp__legendary__*`
- `no_memory_written_in_s1` — the legendary arm wrote nothing to remember

`report.py` prints the excluded count beside every arm.

## Rules

- n >= 10 per arm, interleaved by round so an interrupted run keeps arms
  balanced.
- Identical prompts across arms, fixed in `run_bench.py` and committed.
- A grep gate aborts the run if the fixture contains the quirk keyword.
- ALL runs are published in `bench/results/`, including failures and runs where
  legendary loses. No run is discarded after the fact.
- "Delivered but ignored" is decided by ordering: injection/recall timestamp vs
  the first quirk hit in session 2.
- Author bias disclosed: we wrote legendary. Anyone can re-run this.

## Known limitation (measured, not assumed)

`CLAUDE_CONFIG_DIR` isolation was probed and **rejected**: it strips the
operator's skills and plugins but breaks authentication, because credentials
live in the OS keychain. Trials therefore run with the operator's global config
present — in v1 this meant a `systematic-debugging` skill was active in every
trial, which suppresses exactly the thrashing the benchmark measures.

It affects all arms equally, but results do not represent a stock agent. Every
trial records `operator_env` (slash-command and tool counts) so the
contamination is visible in the published data rather than hidden.

## Running it

```bash
uv run python bench/run_bench.py --arms baseline -n 1 --workdir /tmp/legbench-v2  # smoke
uv run python bench/run_bench.py -n 10 --workdir /tmp/legbench-v2                 # full
uv run python bench/report.py
```

This spends real Claude usage quota (~500k tokens per trial). It is
deliberately not run in CI, and running it is always an explicit decision.
