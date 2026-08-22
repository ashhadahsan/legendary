---
id: mem-ef6ba9d9
type: episode
title: MOCKPAY /refund also reconciles only JSON-string amounts
created: '2026-08-21T11:22:45.072032Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: 09f0aad
  content_hash: sha256:8c14b34ee4b36dc1bfdfeed03523410df558febf990b5ca8d933c699adc5d13d
tags:
- billing
- mockpay
- reconciliation
- refunds
triggers:
- test_refund_reconciliation
- totals['refund'] == pytest.approx(20.00)
- refund reconciles to 0.0
---
The MOCKPAY_URL payments service POST /refund behaves exactly like /batch: returns {"status":"accepted"} for any amount type, but /totals only reconciles amounts sent as JSON **strings**. A numeric amount is silently accepted yet reconciles to refund=0.0. Verified live against the running mock on 2026-08-21: str amounts '12.50'+'7.50' -> totals refund=20.0; numeric -> refund=0.0. Fix in submit_refunds: serialize amount with str(r["amount"]). The prior 'stale'-flagged /batch memory (mem-153e3138) proved STILL ACCURATE despite the stale flag — the string-only quirk persists; verify, don't assume stale==wrong.
