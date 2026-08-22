---
id: mem-4e9c04d9
type: decision
title: submit_refunds implemented; sends amounts as string decimals
created: '2026-08-21T11:06:01.597199Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: bcb2f1d
  content_hash: sha256:645e7b8a6cf452948bae69d48e5f00326ad623efa49098b9c42c776014b9a782
tags:
- billing
- mockpay
- payments
- refunds
triggers: []
---
billing/refunds.py submit_refunds is now implemented (no longer NotImplementedError). It POSTs {"records":[{"id":..., "amount": str(r["amount"])}]} to MOCKPAY_URL/refund. Amounts are serialized as string decimals because the payments mock silently drops JSON-float amounts (see [[mem-c129094c]]). Verified: tests/test_refunds.py::test_refund_reconciliation passes (refund total reconciles to 20.00). The MOCKPAY float-drop quirk was confirmed still present in the actual server at /Users/ashhad/legendary/bench/mockpay.py despite the prior memory being flagged stale.
