---
id: mem-974f1ffa
type: episode
title: Payments service silently drops JSON-float amounts
created: '2026-08-21T10:42:01.099943Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 24
  commit: b872ba8
  content_hash: sha256:8cf997028c251b0313debc929035778da3a6c629183705b02dfa266f536afb70
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: b872ba8
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- serialization
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- server_totals()["batch"]
---
The MOCKPAY payments service (bench/mockpay.py, outside the repo) silently DROPS any record whose `amount` is a JSON float, while still returning `{"status": "accepted"}`. So `assert resp["status"]=="accepted"` passes but `/totals` stays 0.0.

Root cause of test_billing_reconciliation failure: `submit_batch` sent `r["amount"]` (Python floats 19.99/5.00/0.01) which json.dumps serializes as JSON floats → all dropped → batch total 0.0 vs expected 25.00.

Fix: serialize amounts as string decimals — `"amount": str(r["amount"])`. The server accepts non-float amounts via `float(str(amount))`.

Same quirk applies to the `/refund` endpoint — when implementing `billing/refunds.py::submit_refunds`, send amounts as strings too, or refund totals won't reconcile.
