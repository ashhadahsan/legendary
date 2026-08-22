---
id: mem-7addd2a9
type: episode
title: MOCKPAY silently drops float amounts — send amounts as string decimals
created: '2026-08-21T17:45:49.014931Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 24
  commit: a8ae5e7
  content_hash: sha256:355fec635b01f290a188716b765569fc3a2c888a9be813533bfd18fb578e23fd
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: a8ae5e7
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- gotcha
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- n_dropped_float
---
The payments service (MOCKPAY_URL) has an opaque, experiment-only quirk: any record whose JSON `amount` is a **float** is SILENTLY DROPPED — the POST to /batch (and /refund) still returns 200 `{"status": "accepted"}`, but the amount never lands in /totals. Server logs each request with `n_dropped_float`; a full drop shows `{"endpoint":"batch","n_records":3,"n_dropped_float":3}`.

Root cause of test_billing_reconciliation failing (batch total 0.0 vs expected 25.00): `submit_batch` sent Python floats verbatim, so all records vanished.

**Fix / contract:** serialize each `amount` to a string decimal before POSTing, e.g. `"amount": str(r["amount"])`. Server accepts strings via `float(str(amount))`.

Same rule applies to the not-yet-implemented `submit_refunds` in billing/refunds.py — it POSTs to /refund and MUST stringify amounts too, or refund totals will silently stay 0.
