---
id: mem-de14da0c
type: episode
title: Payments service silently drops JSON float amounts in /batch
created: '2026-08-21T17:32:38.215433Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 22
  commit: b927ada
  content_hash: sha256:ac45830d79acc73282ea9e56652865164ac9826d5080e2918c1be7297ef92c0c
tags:
- billing
- payments
- opaque-service
- json-serialization
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- tests/test_billing.py::test_billing_reconciliation
---
The MOCKPAY payments service (URL in MOCKPAY_URL) has an opaque quirk on POST /batch: it returns {"status":"accepted"} but SILENTLY records a value of 0 for any record whose `amount` is a JSON float. It only reads `amount` when sent as a JSON integer (face value) or a JSON string (parsed to float). So sending {"amount": 19.99} records 0, while {"amount": "19.99"} records 19.99 and {"amount": 1999} records 1999.

Fix in billing/client.py submit_batch(): serialize amount as a string — `"amount": str(r["amount"])`. Do NOT send integer cents (that records 2500 instead of 25.00). Endpoints: POST /batch, GET /totals -> {"batch","refund"}, GET /reset. Unknown paths return {"status":"unknown endpoint"}; missing `records` key returns {"status":"bad request"}.

Diagnosed empirically by probing the service; repo memory was empty (recall returned nothing).
