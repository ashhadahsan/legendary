---
id: mem-c41b01ae
type: episode
title: MOCKPAY /refund also only tallies `amount` as a string
created: '2026-08-21T17:27:59.575193Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 23
  commit: 930c2c7
  content_hash: sha256:9cb812a34b90774f4a711beb6e9c0977cb7ef61d62621f82a5d0100e07eb19a9
tags:
- billing
- mockpay
- opaque-service
- refunds
triggers:
- test_refund_reconciliation
- totals["refund"]
- refund reconcile 0.0
---
The payments service (MOCKPAY_URL) `/refund` endpoint has the same quirk as `/batch`: it returns `{"status":"accepted"}` but only adds a record's amount to the refund total when `amount` is a JSON **string** (e.g. "12.50"). Numeric amounts are silently dropped (add $0). Verified by probing: reset then POST {"records":[{"id":"x","amount":1.00}]} gave totals.refund 0.0, while the string form "1.00" gave 1.0.

Fix in `submit_refunds`: `"amount": str(r["amount"])`. Payload shape mirrors submit_batch: {"records":[{"id":..,"amount":str(..)}]}. `tests/test_refunds.py` passes.

Endpoints: POST /refund and /batch, GET /totals -> {"batch","refund"}, GET/POST /reset.
