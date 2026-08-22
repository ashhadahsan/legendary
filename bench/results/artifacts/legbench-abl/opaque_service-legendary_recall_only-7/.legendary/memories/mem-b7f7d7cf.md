---
id: mem-b7f7d7cf
type: episode
title: MOCKPAY /refund only credits amounts sent as JSON strings (same quirk as /batch)
created: '2026-08-21T17:41:26.601913Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 25
  commit: 2387fb6
  content_hash: sha256:3fd5915569d6996f8b24dc9a733b0c8d6522f125b3b1c40bfef87d26fcdb5184
tags:
- billing
- mockpay
- payments
- refunds
triggers:
- tests/test_refunds.py::test_refund_reconciliation
- totals["refund"] == pytest.approx(20.00)
- assert 0.0 == 20.0
---
The MOCKPAY_URL /refund endpoint returns {"status":"accepted"} regardless, but only credits a record's amount toward /totals.refund when `amount` is a JSON string. A raw JSON number is accepted but posted as 0.0 — identical behavior to /batch. Verified empirically against the live service: POST {"records":[{"id":"x","amount":3.00}]} -> totals.refund == 0.0; POST {"records":[{"id":"x","amount":"3.00"}]} -> totals.refund == 3.0. Fix in billing/refunds.py submit_refunds: serialize amount with str(r["amount"]) in the payload, same shape as client.py submit_batch. tests/test_refunds.py::test_refund_reconciliation passes.
