# Benchmark

legendary ships a reproducible, four-arm benchmark rather than asking you to
take a claim on trust. The methodology is **pre-registered and committed**
before any run, so results cannot be retro-fitted to a conclusion.

## What it measures

Two sessions with separate context - the amnesia boundary is the thing under
test:

1. **Session 1** fixes a concurrency bug in `sync/worker.py`. The plausible fix
   (wrapping writes in `BEGIN TRANSACTION`) does *not* work; the working fix is
   `PRAGMA busy_timeout`. The agent learns this the hard way.
2. **Session 2**, with fresh context, fixes the same class of bug in
   `sync/reporter.py`. An agent with no memory of session 1 tends to retry the
   approach that already failed.

The fixture is validated three ways: broken -> both tests fail;
`busy_timeout` -> both pass; `BEGIN TRANSACTION` -> still fails.

## Arms

| Arm | Configuration |
|---|---|
| `baseline` | no memory, no graph tooling |
| `graphify` | Graphify MCP only |
| `legendary` | legendary MCP only |
| `both` | Graphify + legendary |

Graphify is included because it is the nearest well-known tool, and because the
honest hypothesis is that the two are **complementary**: Graphify models code
structure, legendary remembers decisions and failures. If `both` wins, that is
what gets published.

## Metrics

- `tokens_total` - input + cache + output across both sessions
- `cost_usd`, `duration_s`, `num_turns`
- `repeated_failure` - did session 2 reintroduce the known-bad pattern?
  Detected deterministically from the diff, not by an LLM judge.
- `correct` - does the test suite pass at the end?

## Running it

```bash
uv run python bench/run_bench.py -n 5 --workdir /tmp/legbench
uv run python bench/report.py
```

This costs real API credits (40 agent sessions at the default settings) and is
deliberately excluded from CI.

## Results (n=5 per arm, 2026-08-15)

**legendary lost.** Published in full, as pre-registered.

| arm | n | median tokens | median cost | repeated failure | correct |
|---|---|---:|---:|---|---|
| baseline | 5 | **493,288** (458,623-536,701) | **$0.84** | 5/5 | 5/5 |
| legendary | 5 | 571,264 (546,561-694,317) | $1.08 | 5/5 | 5/5 |

- **+16% tokens, +29% cost** versus no memory at all.
- **`repeated_failure` was 5/5 in both arms.** legendary did not prevent
  agents from re-exploring dead ends, which is the single thing it exists to
  prevent.
- Session 2 - where memory should pay off - was **36% more expensive** with
  legendary (316k vs 232k median). The predicted effect ran backwards.
- Correctness was unaffected: every trial in both arms ended green.

### Why - what the data does and does not say

The obvious explanation is that agents ignored the tool. In 2 of 5 trials the
agent never called `remember` at all, so session 2 had nothing to recall while
still paying for five tool definitions in context on every turn.

**But that explanation does not survive the data:**

| legendary trials | session 2 median tokens |
|---|---:|
| memory was saved (n=3) | 342,287 |
| no memory saved (n=2) | 273,378 |
| baseline (n=5) | **232,177** |

Trials *with* a memory available did **worse** than trials without. Having the
memory did not help; it correlated with higher cost. Any story that legendary
would have won "if only the agent had used it" is not supported here.

### Honest caveats, in both directions

1. **n=5 with wide variance.** The subgroup comparison above rests on n=3 vs
   n=2. It is suggestive, not conclusive.
2. **A 2-session task may be too short to amortize.** legendary pays a write
   cost in session 1 and can only recover it in later sessions. Two sessions is
   the worst case for a memory tool; the interesting curve is at 4+.
3. **The benchmark tested a configuration this project does not recommend.**
   Only the MCP server was enabled. The `PreToolUse` surface hook - the
   mechanism specifically designed to deliver memories *without* relying on the
   agent choosing to call `recall` - was **not** configured. That is a real gap
   between what we ship and what we measured, and it is our error, not a
   defence of the result.

### What this changes

The result stands for the configuration tested: **on a two-session task with
MCP tools alone, legendary costs more and prevents nothing.** Until a run with
the hook enabled says otherwise, no token or cost claim belongs in this
project's marketing.

The next run should (a) enable the `PreToolUse` hook, (b) extend to 4+ sessions
so the write cost has a chance to amortise, and (c) persist session transcripts
so we can see whether `recall` was ever called in session 2 - the current
harness discards them, which is why that question is still open.

Raw per-trial JSON for all ten runs is in `bench/results/`.
