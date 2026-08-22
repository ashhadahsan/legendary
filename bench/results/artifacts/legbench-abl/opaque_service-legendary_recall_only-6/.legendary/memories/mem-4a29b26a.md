---
id: mem-4a29b26a
type: episode
title: Payments service /refund silently drops JSON float amounts (same quirk as /batch)
created: '2026-08-21T17:33:43.063218Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 23
  commit: b927ada
  content_hash: sha256:3b85336088b8980f8d4d6b4e47c9cdf5d9a2e2c95f9cbd871f950d52b7b8e85c
tags:
- billing
- payments
- opaque-service
- json-serialization
- refunds
triggers:
- test_refund_reconciliation
- tests/test_refunds.py
- totals["refund"]
- submit_refunds
---
Verified empirically on 2026-08-21: the MOCKPAY payments service (URL in MOCKPAY_URL) has the SAME opaque quirk on POST /refund as on /batch. It returns {"status":"accepted"} but SILENTLY records 0 for any record whose `amount` is a JSON float. It only reads `amount` when sent as a JSON string (parsed to float) or a JSON integer (face value).

Probed /refund with a single amount=10.0 record: JSON float 10.0 -> totals.refund=0; JSON string "10.0" -> totals.refund=10.0; JSON int 10 -> totals.refund=10.0. Since real amounts have cents (e.g. 12.50, 7.50), integers lose the decimal, so use STRING.

Fix in billing/refunds.py submit_refunds(): serialize as `"amount": str(r["amount"])`, POST {"records":[...]} to /refund. This makes tests/test_refunds.py::test_refund_reconciliation pass (12.50+7.50 reconciles to 20.00). Same fix pattern as billing/client.py submit_batch(). Endpoints: POST /batch, POST /refund, GET /totals -> {"batch","refund"}, GET /reset. The prior /batch memory (mem-de14da0c) was flagged stale but its core quirk still holds.
