# Benchmark Generalization — Three More Scenario Shapes

**Date:** 2026-08-21
**Status:** Design
**Motivation:** The n=10 result (9.5x fewer rediscoveries, p=0.00015) holds on
*one* scenario that we designed. The obvious and fair objection is that the
fixture was built to show the effect. Generalization is the difference between
"interesting result" and "property of the tool".

## The bar each scenario must clear

Every scenario must satisfy the four properties that made `scenario2` valid,
and must be validated against them *before* any trial counts:

1. **Unrecoverable from the repo.** The needed knowledge must not exist in any
   file the agent can read. Enforced by a grep gate.
2. **Behavioral metric.** Rediscovery is counted by an oracle observing what
   the agent *did*, never by matching text that might also appear in source.
3. **Plausible fixes genuinely fail.** The intuitive remedies must not work, or
   the task doesn't discriminate.
4. **Hard reset between sessions.** Session 1's code changes are reverted, so
   memory is the only channel.

## Why three *different oracles*

`scenario2` uses an HTTP mock as the oracle. Building three more HTTP mocks
would test one shape four times. Each new scenario uses a structurally
different oracle, so a result that holds across all four is much harder to
attribute to fixture design.

| # | Scenario | Knowledge type | Oracle |
|---|---|---|---|
| 2 | opaque service drops float amounts | external API behavior | HTTP server log (existing) |
| 3 | reverted approach | **negative knowledge about our own code** | git diff (safe here — see below) |
| 4 | silent truncation above a batch size | external shape constraint | HTTP server log |
| 5 | migration tool no-ops without a flag | **local tooling behavior** | wrapper-process invocation log |

## Scenario 3 — the reverted approach

The purest test of the `episode` type, and the one closest to the real use
case: *"we tried this and it did not work."*

- **Session 1:** `cache/warm.py` must pre-populate a cache before a deadline.
  The obvious implementation — spawning a background thread per key — passes
  locally but fails the supplied test under load (thread explosion; the test
  asserts a bounded worker count). The working approach is a bounded pool.
  The agent tries threads, fails, reverts, and lands on the pool.
- **Reset.** Both the failed attempt *and* the fix disappear.
- **Session 2:** the sibling `cache/refresh.py` needs the same treatment.
- **Metric:** does session 2's diff contain the thread-per-key signature
  (`Thread(target=`)?

**Why the diff metric is safe here** (v1's fatal flaw was a diff/text metric):
in v1 the dead-end pattern `busy_timeout` was *present in the fixture's own
source*, so reading a file scored as a failure. Here the pattern is
`Thread(target=` and the fixture contains **no** `threading` import anywhere —
enforced by the grep gate. The only way the string can appear in the diff is if
the agent *wrote* it. The metric counts authorship, not reading.

## Scenario 4 — silent truncation above a batch size

- **Service:** accepts `POST /ingest`; if a request contains more than 5
  records it silently keeps the first 5 and returns `200 {"accepted": N}` where
  N is the number *sent*, not stored. Reconciliation fails.
- **Plausible failures:** retry (no error to retry), timeout increase (fast
  response), checking the status code (it is 200 and the count "matches").
- **Session 2:** a different endpoint with the same cap.
- **Metric:** count of requests with >5 records, from the server log.

## Scenario 5 — the migration tool that no-ops

Tests knowledge about *local tooling*, not a network service.

- **Tool:** `bin/migrate` (a harness-provided wrapper) applies schema
  migrations. Without `--apply` it performs a dry run, prints
  `migration plan ready` and exits **0** — writing nothing. The obvious reading
  is that it succeeded.
- **Plausible failures:** re-running it, checking the exit code (0), reading
  its `--help` (the harness wrapper's help is deliberately terse and does not
  explain the default).
- **Session 2:** a second migration must actually be applied.
- **Metric:** count of `bin/migrate` invocations lacking `--apply`, from the
  wrapper's own invocation log (written outside the repo).

## Reporting

`report.py` gains a per-scenario breakdown plus a pooled row. **Every scenario
is published whether or not it favors legendary** — a mixed result across four
shapes is a more useful finding than a clean sweep on one, and pretending
otherwise would forfeit the credibility the retraction bought.

Pre-registration lives in `bench/README.md` and is committed before any run.

## Cost

Each scenario is 2 sessions/trial, ~$1.20/trial. n=10 x 2 arms x 3 new
scenarios ≈ 120 sessions ≈ **$70 and ~15M tokens**. This is a substantial
quota decision and must be made explicitly, per scenario if preferred — the
harness takes `--scenario`, so they can be run one at a time.
