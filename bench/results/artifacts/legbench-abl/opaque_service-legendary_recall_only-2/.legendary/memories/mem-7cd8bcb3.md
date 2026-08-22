---
id: mem-7cd8bcb3
type: episode
title: Payments service only reconciles string amounts, not floats
created: '2026-08-21T17:08:22.217819Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 21
  commit: 87f3ba7
  content_hash: sha256:24dc520db5e1899d1601d858715ee8c71c90e402fc622c298590e4b65dd50b23
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 4
  - 6
  commit: 87f3ba7
  content_hash: sha256:5d03e67321daa651911d036ef7f11dc63bba4b753283634cf7a8f9f2259f8db8
tags:
- billing
- opaque-service
- reconciliation
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- server_totals()["batch"]
---
The opaque payments service (MOCKPAY_URL) `/batch` and `/refund` endpoints return `{"status":"accepted"}` for float `amount` values but silently DROP them from `/totals` (records 0.0). It only sums `amount` when sent as a **decimal string** (e.g. `"19.99"`). Integer amounts are summed literally (1999 -> 1999.0, NOT cents).

Fix for `submit_batch` in billing/client.py: serialize amount with `str(r["amount"])` in the payload. Same pattern will be needed for `submit_refunds` in billing/refunds.py (POST to /refund).

Probe the live server to discover shape: `curl $MOCKPAY_URL/reset` then POST and check `/totals`.
