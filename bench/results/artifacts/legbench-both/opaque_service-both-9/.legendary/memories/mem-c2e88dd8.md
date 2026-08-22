---
id: mem-c2e88dd8
type: decision
title: MOCKPAY service records amount only as a decimal string
created: '2026-08-21T16:12:37.451750Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 21
  commit: 3b0b5d4
  content_hash: sha256:ee375a38935b8216b753067e4ab15bf764497e3f358a71e306a59361603df73b
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: 3b0b5d4
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- opaque-service
triggers: []
---
The opaque payments service at MOCKPAY_URL (/batch, /refund, /totals, /reset) records a record's `amount` ONLY when sent as a JSON string (e.g. "19.99"). A JSON number is silently accepted ("status":"accepted") but recorded as 0.0. Probed empirically: string "19.99" -> batch 19.99; number 19.99 -> batch 0.0. Fix in submit_batch: json-encode amount as str(r["amount"]). When implementing submit_refunds in billing/refunds.py (POST /refund), apply the same str() conversion so refund totals reconcile.
