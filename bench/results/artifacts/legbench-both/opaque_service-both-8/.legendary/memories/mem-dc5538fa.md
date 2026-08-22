---
id: mem-dc5538fa
type: episode
title: MOCKPAY /batch expects amount as a string, not a JSON number
created: '2026-08-21T16:10:04.372756Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 21
  commit: 36a7896
  content_hash: sha256:429548bc1cbd4ff57f494670f85e7532799e17f8fac3318e3c734f7db0bfcdc2
tags:
- billing
- mockpay
- serialization
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- 'batch": 0.0'
---
The mock payments service (MOCKPAY_URL) parses each record's `amount` from a STRING. Sending a JSON number (float) is silently accepted ("status":"accepted") but recorded as 0, so /totals reports batch=0.0. Sending amount as a string like "19.99" parses correctly and sums into the batch total. Fix in billing/client.py submit_batch: serialize `str(r["amount"])`. Probed via curl: float 19.99 -> total 0.0; "19.99" -> 25.0; int 19 -> 19.0 (ints also parse, but the real API/tests use decimal dollars, so strings are the correct form). Same quirk almost certainly applies to submit_refunds (/refund) in billing/refunds.py, which is currently a NotImplementedError stub.
