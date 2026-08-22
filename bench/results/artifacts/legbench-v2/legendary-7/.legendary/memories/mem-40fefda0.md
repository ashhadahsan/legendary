---
id: mem-40fefda0
type: episode
title: MOCKPAY silently drops float amounts — send amounts as string decimals
created: '2026-08-21T11:11:10.254369Z'
source: agent
status: deprecated
deprecated_reason: superseded by mem-18792764
superseded_by: mem-18792764
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 22
  commit: '3594124'
  content_hash: sha256:06355099b38cfbaddab236a521d0fdc097404724d1d56eb4332702a8f26e292c
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: '3594124'
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- reconciliation
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- n_dropped_float
- test_refund_reconciliation
---
The payments mock (bench/mockpay.py, external to repo) has an opaque quirk: any record whose `amount` is a JSON **float** is SILENTLY DROPPED at /batch and /refund — the response is still 200 {"status": "accepted"}, so it looks fine but totals stay 0.0. Non-float amounts are summed via `float(str(amount))`, so amounts MUST be serialized as **string decimals** (e.g. "19.99"). Diagnosed via /tmp/legbench-v2/legendary-7-mockpay.jsonl showing `n_dropped_float` == n_records.

Fix applied in billing/client.py submit_batch: `"amount": str(r["amount"])`.

NOTE: billing/refunds.py submit_refunds has the SAME requirement — when implemented it must send string amounts too, or test_refund_reconciliation will silently reconcile to 0.
