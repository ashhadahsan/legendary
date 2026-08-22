---
id: mem-e0b3a597
type: episode
title: MOCKPAY /refund also requires string decimal amounts (same quirk as /batch)
created: '2026-08-21T17:03:51.629097Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: 0c9013b
  content_hash: sha256:f5e1c24642a5e1ae7e4df5d710764fd5ce1d9ce4d1214c53f3cd4da628b483c3
tags:
- billing
- mockpay
- opaque-service
- refunds
triggers:
- tests/test_refunds.py::test_refund_reconciliation
- totals["refund"] == 0.0
- assert totals["refund"] == pytest.approx(20.00)
---
Verified live (2026-08-21) against MOCKPAY_URL: the `/refund` endpoint behaves exactly like `/batch` — it returns `{"status":"accepted"}` regardless, but only ADDS a record's `amount` to `/totals["refund"]` when `amount` is serialized as a JSON **string** decimal (e.g. "19.99"). A JSON number (float 19.99) is accepted but NOT counted (totals stay 0.0).

Top-level payload key must be `records`. So `submit_refunds` in billing/refunds.py serializes with `str(r["amount"])`, mirroring `submit_batch` in billing/client.py.

Probe recipe: `curl $MOCKPAY_URL/reset`; POST `{"records":[{"id":"x","amount":"19.99"}]}` to `/refund`; GET `/totals` → `{"batch":0.0,"refund":19.99}`. With a float amount, refund stays 0.0.

This confirms the string-decimal quirk was still current at commit 0c9013b despite the /batch memory being flagged stale.
