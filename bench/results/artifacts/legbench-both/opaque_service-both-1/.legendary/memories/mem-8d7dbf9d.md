---
id: mem-8d7dbf9d
type: decision
title: MOCKPAY silently drops float amounts; send amounts as string decimals
created: '2026-08-21T15:46:25.951412Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 26
  commit: 76201f7
  content_hash: sha256:f37d65d64411400f11845c366bfc37cb53539ad4ff3987d348b157e5203f3f07
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 19
  commit: 76201f7
  content_hash: sha256:77288785d24bdc4e0969feb00fc636764042c8d77d0c44589cf2ae1b7ee397a4
tags:
- mockpay
- payments
- quirk
- opaque-service
triggers: []
---
The payments service at MOCKPAY_URL (/batch and /refund endpoints) has a quirk: any record whose `amount` is a JSON float is SILENTLY DROPPED — the response is still 200 {"status": "accepted"} but the amount is NOT added to server-side totals. Amounts must be sent as string decimals (e.g. "12.50") to be counted; the server does float(str(amount)).

billing/refunds.py::submit_refunds handles this by sending {"amount": str(r["amount"])}. NOTE: billing/client.py::submit_batch still sends raw floats (r["amount"]), so it has the same latent bug — batch totals will silently fail to reconcile for float amounts. Fix it the same way if batch reconciliation matters.

Verified: pytest tests/test_refunds.py passes (totals["refund"] == 20.00 for two float records).
