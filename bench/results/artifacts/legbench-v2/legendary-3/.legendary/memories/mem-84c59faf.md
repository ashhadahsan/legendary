---
id: mem-84c59faf
type: episode
title: mockpay /refund records float amounts as 0.0 — send amounts as strings (verified)
created: '2026-08-21T10:48:37.788067Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 28
  commit: 6c072e5
  content_hash: sha256:97e32ac2a277d3bd4f4ea53558c92d8b24f39a61d2ec28811e3d4791409e8d1b
tags:
- billing
- mockpay
- serialization
- refunds
triggers:
- totals["refund"] == 0.0
- test_refund_reconciliation
- assert totals["refund"] == pytest.approx(20.00)
---
Implemented `submit_refunds` in billing/refunds.py. Verified live against MOCKPAY_URL: POSTing `{"records":[{"id","amount"}]}` to /refund returns `{"status":"accepted"}` but records the amount as 0.0 when `amount` is a JSON float; sending it as a JSON string (e.g. "12.50") tallies correctly in /totals["refund"]. Same quirk as /batch — see [[mem-fa7ca893]] (its client.py anchor went stale after 6c072e5, but I re-probed with curl and the float→0.0 behavior still holds on both /batch and /refund).

Fix used: serialize each amount with `format(r["amount"], ".2f")` before json.dumps. `pytest tests/test_refunds.py` passes (refund total reconciles to 20.00 for records summing 12.50+7.50).
