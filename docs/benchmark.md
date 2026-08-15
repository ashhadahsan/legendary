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

## Results

### Preliminary smoke run (n=1 per arm) - NOT a claim

One trial per arm, run to validate the harness. **This is not statistically
meaningful** and should not be quoted as evidence. The pre-registered protocol
requires n>=5 with median and range; those numbers will replace this section.

| metric | baseline | legendary |
|---|---:|---:|
| tokens total | 1,108,794 | 864,798 (-22%) |
| wall clock | 144.8 s | 96.2 s (-34%) |
| cost | $0.95 | $1.04 (**+9%**) |
| repeated_failure | False | False |
| correct | True | True |

Per-session split, which is where the predicted mechanism shows up:

| | baseline | legendary |
|---|---:|---:|
| session 1 | 355,446 | 461,013 (pays to write memory) |
| session 2 | 753,348 | **403,785** |

Baseline's second session cost roughly twice its first, re-deriving what it had
just worked out. legendary's second session used ~46% fewer tokens than
baseline's.

### Honest caveats

1. **n=1 proves nothing.** Agent runs vary widely - baseline's own two sessions
   differed by 2x.
2. **Cost rose 9% despite 22% fewer tokens.** The token mix shifted toward
   uncached input. "Fewer tokens and faster" is supportable so far; "cheaper"
   is not.
3. **`repeated_failure` did not discriminate** (False for both arms). The
   scenario let agents fix the bug with `sqlite3.connect(timeout=...)`, a
   legitimate alternative sitting right next to the intended `BEGIN
   TRANSACTION` trap, so neither arm was tempted into it. That is a flaw in the
   fixture design, not a finding about the tools. A future revision needs a bug
   whose *obvious* fix is genuinely wrong. The metric stays in the
   pre-registration and is reported as "did not discriminate" rather than
   dropped.

Raw per-trial JSON for every run, including this one, is committed under
`bench/results/`. See `bench/README.md` for the pre-registration.
