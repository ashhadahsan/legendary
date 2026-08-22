---
id: mem-fe819bd2
type: episode
title: MOCKPAY /refund still drops float amounts — submit_refunds stringifies (verified
  2026-08-21)
created: '2026-08-21T17:46:54.318268Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: a8ae5e7
  content_hash: sha256:aef7e0fbdf2d4dd2e2efaf68fd5867e98c4ade3249546cd0b6411930f85d39a1
tags:
- billing
- mockpay
- gotcha
- refunds
triggers:
- test_refund_reconciliation
- refund total 0
- totals refund 0.0
- n_dropped_float
---
Re-verified the MOCKPAY float-drop quirk directly against the live server (mem-7addd2a9 was flagged stale because billing/client.py:submit_batch changed, but the server contract still holds for /refund).

Empirical probe: POST /refund with float amounts (12.5, 7.5) returns 200 {"status":"accepted"} but /totals shows refund=0.0. POST the same amounts as string decimals ("12.5","7.5") yields refund=20.0. So floats are still silently dropped; strings reconcile.

Implemented billing/refunds.py:submit_refunds accordingly — mirrors submit_batch but POSTs to /refund and serializes each amount via str(r["amount"]). tests/test_refunds.py::test_refund_reconciliation passes (refund total 20.00).

Lesson: don't blindly trust OR blindly dismiss a stale memory — verify against the server. Here the stale flag reflected an unrelated code change, not an invalidated contract.
