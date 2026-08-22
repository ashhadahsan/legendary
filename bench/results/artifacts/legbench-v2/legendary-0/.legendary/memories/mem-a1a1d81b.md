---
id: mem-a1a1d81b
type: episode
title: MockPay /batch (and /refund) ignore JSON-float amounts — send decimal strings
created: '2026-08-21T10:26:16.218041Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 26
  commit: 1497aad
  content_hash: sha256:5ab792d1d16115b9424a95a1f8caa03cb46005da8c7da75e5acb030be20b1cf9
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: 1497aad
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- mockpay
- serialization
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- server_totals()["batch"]
- 'status": "accepted'
---
The MOCKPAY payments service silently drops `amount` values sent as JSON floats: POST /batch still returns {"status":"accepted"} but /totals stays 0.0. It only records amounts sent as decimal STRINGS (e.g. "19.99") or integers. Fix in billing/client.py submit_batch: serialize amount via format(float(r["amount"]), ".2f") instead of passing the raw float.

Other verified server quirks:
- Reset is GET /reset (returns {"status":"reset"}); POST /reset => "unknown endpoint". The test fixture uses urlopen (GET), so that's fine.
- Payload must be {"records":[{"id":..,"amount":..}]}. A bare list or {"items":[...]} => {"status":"bad request"}.
- /totals returns {"batch": float, "refund": float}.

Applies equally to submit_refunds in billing/refunds.py (POST /refund) — same string-amount requirement will be needed there.
