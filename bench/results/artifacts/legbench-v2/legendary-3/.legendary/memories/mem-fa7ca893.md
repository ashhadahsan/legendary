---
id: mem-fa7ca893
type: episode
title: mockpay records JSON float amounts as 0.0 — send amounts as strings
created: '2026-08-21T10:47:31.015273Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 23
  commit: 6c072e5
  content_hash: sha256:2c653a8ccf5f6f41e0e60f392ab43e23004aa97ecc0e795198dc81ab57b480c4
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: 6c072e5
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- serialization
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- 'batch": 0.0'
---
The mockpay payments service (MOCKPAY_URL) returns `{"status":"accepted"}` for a /batch POST but silently records the amount as 0.0 when `amount` is a JSON float. It correctly tallies amounts sent as JSON strings (e.g. "19.99") or integers.

Fix in `submit_batch` (billing/client.py): serialize amount with `format(r["amount"], ".2f")` so it goes over the wire as a string.

Same quirk applies to the /refund endpoint — when implementing `submit_refunds` in billing/refunds.py, send amounts as strings too, or refund totals will reconcile to 0.0.
