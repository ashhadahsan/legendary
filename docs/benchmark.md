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

## Scenario 2 result: legendary wins (n=10)

*(table and analysis above)*

## Head-to-head vs mem0 (n=10 per arm, same scenario)

The first comparison against a memory tool people actually use, rather than
against nothing.

| arm | n | median rediscoveries | range | s2 cost | s2 correct |
|---|---|---|---|---|---|
| baseline | 10 | 9.5 | 1-15 | $0.60 | 10/10 |
| mem0 | 10 | **11.5** | 0-26 | **$0.77** | 10/10 |
| legendary | 10 | **1.0** | 0-2 | $0.60 | 10/10 |

```
baseline  [1, 6, 7, 7, 9, 10, 10, 12, 12, 15]   = 89 wasted requests
mem0      [0, 0, 4, 7, 11, 12, 12, 15, 24, 26]  = 111
legendary [0, 1, 1, 1, 1, 1, 2, 2, 2, 2]        = 13
```

- legendary vs mem0: **p = 0.00705**
- mem0 vs baseline: **p = 0.695** - mem0 was statistically indistinguishable
  from having no memory at all on this task, while costing 28% more per
  session.

### Does running both together help? No.

| arm | n | median | raw | total rediscoveries |
|---|---|---|---|---|
| mem0 | 10 | 11.5 | | 111 |
| both | 10 | **1.0** | `[0,0,1,1,1,1,5,5,9,20]` | 43 |
| legendary | 10 | **1.0** | `[0,1,1,1,1,1,2,2,2,2]` | **13** |

Same median, but no measurable benefit and clearly worse stability: legendary
alone never exceeded 2 rediscoveries in any trial, while the combination
produced a 9 and a 20 - worse than baseline's worst trial. Total waste more
than tripled.

`both` vs `legendary` is **p = 0.36**, so we do *not* claim combining is worse.
We claim it does not help. Adding legendary to mem0, by contrast, does help
significantly (p = 0.048).

**Verdict: legendary is standalone.** There is no memory tool to bolt it onto,
and no benefit measured from doing so.

### Two explanations we tested and rejected

**"mem0 never got used."** False. Counting actual tool invocations (not
ToolSearch lookups - an early count of ours conflated the two), mem0 stored in
**10/10** trials and was searched in **9/10**. It was used as intended.

**"mem0 stored worse knowledge."** Also false. Its memories were correct and
detailed, capturing the full service contract including the quirk. Content was
not the problem.

### What differed - and a correction

An earlier version of this page claimed legendary's `guard` hook "fired in
10/10 trials, pushing the fix back at the moment the failure recurred." **That
claim went further than the evidence supports, and is withdrawn.**

What the data actually shows:

- A push hook fired in 10/10 legendary trials (`hook_fired`), but `surface` and
  `guard` write to the **same** `.surfaced-<session>` cache file, so that flag
  cannot distinguish which one ran.
- The harness records only assistant messages, so hook-injected context does
  not appear in the saved transcripts at all. We cannot see what was delivered.
- `recall` was actively called in 9/10 legendary trials. In the one trial where
  it was not (trial 8), rediscoveries were still low (2), which is suggestive of
  a hook contributing - but a single trial is not evidence.

So the honest statement is: **legendary's combination of push hooks plus
agent-initiated recall outperformed mem0's search-only channel, and we have not
isolated which part is responsible.** The delivery-timing explanation remains
our hypothesis, not a measured result.

What is measured and not in doubt: both tools stored correct knowledge, both
were used as intended, and the outcomes differed by an order of magnitude.

### Deciding what earns its cost

Attribution requires an ablation - separate arms for guard-only, surface-only,
and MCP-only - which has not been run. Until it is, we cannot say which
capability pays for itself, and we will not imply otherwise. Scenario 3 already
showed the whole package costing 54% more for no benefit when the knowledge was
not needed; a per-channel breakdown is the next thing worth measuring. mem0 is a mature tool with
capabilities legendary does not have - semantic search, cross-application
memory, scale. On this task, none of that substituted for arriving at the right
moment.

### Fairness

- The mem0 adapter is ours and is published (`bench/mem0_mcp.py`) for audit:
  two tools mapping onto `Memory.add`/`Memory.search`, no tuning either way.
- We pinned **current** Gemini models because mem0's built-in defaults point at
  a retired one. That change helps mem0.
- mem0 got the same activation assertion as every arm; zero trials excluded.
- baseline and legendary numbers are the same n=10 runs reported above, on the
  same fixture and machine. Only the mem0 arm was run fresh.
- We wrote legendary. Anyone can re-run this: the harness, adapter, fixture,
  and every transcript are committed.

## Scenario 3 result: legendary LOSES (n=10)

A second scenario, deliberately different: negative knowledge about our own
code (an approach tried and reverted), measured by authorship in the git diff
rather than a server log.

| arm | n | median s2 rediscoveries | s2 turns | s2 cost | s2 correct |
|---|---|---|---|---|---|
| baseline | 10 | **0.0** | 8 | **$0.32** | 10/10 |
| legendary | 9 (1 excluded) | **0.0** | 10 | **$0.50** | 9/9 |

**The metric never fired for either arm.** No agent wrote the dead-end pattern
even once. And legendary cost **56% more per session-2** ($0.50 vs $0.32), and
54% more across the whole run ($11.40 vs $7.40), for no measurable benefit.

### Why it failed - a design error in the scenario, not a defect in the tool

The agent went straight to `ThreadPoolExecutor(max_workers=...)`. It never
attempted thread-per-key, so there was nothing to remember and nothing to
avoid.

The mistake was ours: "use a bounded pool rather than unbounded threads" is
**standard knowledge the model already has**. We made it absent from the
repository but not absent from the model's priors. Scenario 2 works because
"this particular service silently discards JSON floats" is *arbitrary* - it
cannot be guessed, only observed.

**This adds a fifth bar every scenario must clear:** the knowledge must be
unavailable to the *model*, not merely absent from the *repo*.

### What the two results say together

This is the more useful finding, and more honest than a clean sweep:

| when the needed knowledge is... | legendary |
|---|---|
| arbitrary, discoverable only by experiment (scenario 2) | **9.5x fewer rediscoveries**, p=0.00015 |
| already in the model's priors (scenario 3) | **~54% more expensive, no benefit** |

legendary is not free. It costs real tokens on every session, and on tasks
where the model already knows the answer that cost buys nothing. It pays off
when your codebase has arbitrary, hard-won, environment-specific knowledge -
which is exactly the knowledge that has no home in a comment or a README.

Use it for the second kind of problem. We would rather say that than sell it
as a universal win.

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
