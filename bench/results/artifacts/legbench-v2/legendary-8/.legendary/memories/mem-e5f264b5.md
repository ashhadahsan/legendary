---
id: mem-e5f264b5
type: episode
title: MockPay /refund sums amount only when sent as a JSON string
created: '2026-08-21T11:18:12.627132Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 23
  commit: 98cb433
  content_hash: sha256:7ce7e202155c6b455c1c93734959811b7a08dedafa512288ce677e14211262b8
tags:
- billing
- mockpay
- money-as-string
- refunds
triggers:
- test_refund_reconciliation
- totals["refund"]
- assert 0.0 == 20.0
---
Empirically probed the live MockPay server (MOCKPAY_URL): POST /refund follows the SAME money-as-string contract as /batch. It returns {"status":"accepted"} regardless, but only sums a record's `amount` into the refund total when `amount` is a JSON string (e.g. "12.50"). A JSON float is silently dropped (recorded 0.0); a JSON int is summed raw (1250 -> 2000.0, no cents scaling). Verified: string "12.50"+"7.50" -> refund total 20.0, matching test_refund_reconciliation's pytest.approx(20.00).

Implemented billing/refunds.submit_refunds mirroring client.submit_batch but serializing amount as str(r["amount"]). tests/test_refunds.py passes.

Note: billing/client.submit_batch still sends amount as a raw float, so under this contract test_billing_reconciliation would get batch total 0.0. Out of scope here (task was refunds only) but likely a latent bug.
