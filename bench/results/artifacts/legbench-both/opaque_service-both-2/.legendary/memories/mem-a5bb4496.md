---
id: mem-a5bb4496
type: episode
title: MOCKPAY /refund reconciles only decimal-STRING amounts (re-verified)
created: '2026-08-21T15:49:32.954937Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: f4e4aa9
  content_hash: sha256:b7c3d26fa7d7c9d7120e1341d90c3bdbe6b0bd49b866984558c9c7dee07053ca
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 19
  commit: f4e4aa9
  content_hash: sha256:77288785d24bdc4e0969feb00fc636764042c8d77d0c44589cf2ae1b7ee397a4
tags:
- billing
- mockpay
- opaque-service
- reconciliation
- refunds
triggers:
- test_refund_reconciliation
- test_billing_reconciliation
- refund total 0.0
- totals reconcile
---
Re-verified against the live MOCKPAY service (2026-08-21) while implementing submit_refunds. The /refund endpoint silently ignores `amount` sent as JSON floats: returns {"status":"accepted"} but adds 0 to server-side totals. Probed: float 19.99 -> refund total 0.0; string "19.99" -> 19.99; int 1999 -> 1999.0 (summed literally, wrong scale). So amounts MUST be serialized as decimal strings, str(r["amount"]).

Implemented billing/refunds.py:submit_refunds to POST {"records":[{"id":..., "amount":str(r["amount"])}]} to /refund. test_refunds.py::test_refund_reconciliation passes (RECORDS 12.50+7.50 -> refund total 20.00).

NOTE: current billing/client.py:submit_batch sends `amount` as a RAW FLOAT (r["amount"]), not str(...). Per this service behavior that means /batch totals would NOT reconcile — if test_billing fails, submit_batch likely needs the same str() fix. The prior memory (mem-b4ce7255) claimed submit_batch already used str(), but the code was reverted to raw float since commit f4e4aa9.
