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

## Results (n=10 per arm, 2026-08-21)

**legendary reduced rediscovery ~9.5x.** Zero trials excluded; both channels
activated in 10/10 legendary trials.

| arm | n | median s2 quirk hits | range | s2 cost | s2 turns | s2 correct |
|---|---|---|---|---|---|---|---|
| baseline | 10 | **9.5** | 1-15 | $0.60 | 16 | 10/10 |
| legendary | 10 | **1.0** | 0-2 | $0.60 | 14 | 10/10 |

Raw per-trial counts:

```
baseline:  [1, 6, 7, 7, 9, 10, 10, 12, 12, 15]   -> 89 wasted requests
legendary: [0, 1, 1, 1, 1, 1,  2,  2,  2,  2]    -> 13
```

Exact permutation test (one-sided, 20k resamples): **p = 0.00015**. The
distributions barely touch - only baseline's best trial (1) reaches
legendary's worst (2). One legendary trial rediscovered the quirk **zero**
times: it recalled what the earlier session learned and got the request right
first try.

### What this does and does not show

**Does:** on knowledge that provably cannot be recovered from the repository,
pushed and verified memory stops an agent re-deriving what it already learned.
That is measured behaviorally, from the mock server's own request log, on a
metric that cannot match repository text.

**Does not:** show a cost or token win. Median session-2 cost was **identical**
($0.60 vs $0.60) and turns barely moved (16 vs 14). legendary spent its saved
effort inside the same budget rather than finishing cheaper. Anyone quoting
this as "legendary makes agents cheaper" is misreading it.

**Correctness was unaffected** - 10/10 in both arms. This task is solvable
either way; the difference is how much waste it takes.

### Caveats

1. **One scenario, one model, one day.** External validity is unproven.
2. **Operator config contaminated every trial** (see the known limitation in
   `bench/README.md`): `CLAUDE_CONFIG_DIR` isolation breaks keychain auth, so
   the operator's skills were present in both arms. Each trial records
   `operator_env`; results do not represent a stock agent.
3. **A harness bug was fixed mid-run.** The activation assertion read the init
   event's tool list, which does not enumerate MCP tools, so it was excluding
   legendary trials in which `used_recall` and `used_remember` were both
   recorded and memories existed on disk. The fix recomputes activation from
   observed use, using data captured before the change. Both the bug and the
   fix are in git history. It moved the result in legendary's favour, so it
   deserves the scrutiny.
4. **We wrote legendary.** The methodology was pre-registered and committed
   before the run; anyone can re-run it.

Raw per-trial JSON and full session transcripts for all 20 trials are in
`bench/results/`.

### History

The v1 benchmark reported the opposite (legendary costing more) and was
retracted for measuring nothing - its fixture let session 2 read session 1's
fix, and its headline metric matched strings in the fixture's own source. That
retraction, and the four defects behind it, are what this design was built to
make impossible.
