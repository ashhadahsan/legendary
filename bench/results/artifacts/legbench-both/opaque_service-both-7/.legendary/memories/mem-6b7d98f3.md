---
id: mem-6b7d98f3
type: decision
title: MOCKPAY server drops JSON float amounts — send amounts as strings
created: '2026-08-21T16:08:38.415048Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: 4f70425
  content_hash: sha256:e703e269c9ebfdb8dc820e037289895f1c5eed77eb8d672ac529a0c6b895d286
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 19
  commit: 4f70425
  content_hash: sha256:77288785d24bdc4e0969feb00fc636764042c8d77d0c44589cf2ae1b7ee397a4
tags:
- billing
- mockpay
- gotcha
triggers: []
---
The MOCKPAY payments service (MOCKPAY_URL, /batch and /refund endpoints) silently returns {"status":"accepted"} but only accumulates a record's `amount` into /totals if the amount is a JSON string or integer. Bare JSON floats (e.g. 19.99) are dropped and contribute 0 to reconciliation. Envelope must be {"records":[{"id","amount"}]} (the `records` key is required, else "bad request").

billing/refunds.py works because it serializes amount as str(r["amount"]) before POSTing to /refund.

WARNING: billing/client.py:submit_batch posts r["amount"] as a raw float, so it does NOT reconcile server-side — test_billing.py (expects batch total 25.00) will fail against this server until submit_batch also stringifies amounts.
