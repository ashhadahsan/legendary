---
id: mem-b4ce7255
type: episode
title: MOCKPAY payments service only reconciles decimal-STRING amounts
created: '2026-08-21T15:48:28.504411Z'
source: agent
status: deprecated
deprecated_reason: superseded by mem-a5bb4496
superseded_by: mem-a5bb4496
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 22
  commit: f4e4aa9
  content_hash: sha256:83c9d81ae11323708854a5b3681c97238cc211c5faaacc90c906ce939c49932c
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: f4e4aa9
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- opaque-service
- reconciliation
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- 'batch": 0.0'
---
The opaque payments service at MOCKPAY_URL (endpoints /batch, /refund, /totals, /reset) silently ignores `amount` fields sent as JSON floats — it returns {"status":"accepted"} but adds 0 to server-side totals. Verified by probing: float 19.99 -> total 0.0; integer 1999 -> total 2500 (summed literally as-is, i.e. wrong scale/cents); string "19.99" -> total 19.99. So amounts MUST be serialized as decimal strings (str(amount)) for totals to reconcile. Fix for test_billing_reconciliation: submit_batch now sends {"amount": str(r["amount"])}. The unimplemented submit_refunds (billing/refunds.py) must POST the same {"records":[{"id","amount":str(...)}]} shape to /refund.
