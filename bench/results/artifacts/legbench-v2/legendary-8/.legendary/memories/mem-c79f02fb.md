---
id: mem-c79f02fb
type: episode
title: MockPay /batch counts amount only when sent as a decimal string
created: '2026-08-21T11:17:02.325657Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 21
  commit: 98cb433
  content_hash: sha256:36fc7f21f035450a65a37ab57f9fab1c3208aa315822317853f24c9ba5e6e1b3
tags:
- billing
- mockpay
- money-as-string
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- server_totals()["batch"]
---
The payments service (MOCKPAY_URL) at POST /batch returns {"status":"accepted"} regardless of payload, but only sums a record's `amount` into the batch total when `amount` is a JSON **string** (e.g. "19.99"). A JSON float is silently dropped and recorded as 0.0; a JSON int is summed raw (no cents scaling). Fix in billing/client.submit_batch: serialize `amount` as `str(r["amount"])`. Same contract almost certainly applies to the unimplemented /refund endpoint in refunds.submit_refunds.
