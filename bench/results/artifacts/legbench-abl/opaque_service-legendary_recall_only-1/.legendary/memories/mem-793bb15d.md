---
id: mem-793bb15d
type: episode
title: MOCKPAY /batch silently drops JSON-float amounts; requires string decimals
created: '2026-08-21T17:02:48.481357Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 21
  commit: 0c9013b
  content_hash: sha256:22c878dc647af7a51e862f5b7f648662caf76b17c9a53c612115c46ed2f35e15
tags:
- billing
- mockpay
- opaque-service
triggers:
- test_billing_reconciliation
- assert 0.0 == 25.0
- server_totals()["batch"]
---
The opaque payments service (MOCKPAY_URL) `/batch` endpoint returns `{"status":"accepted"}` regardless, but only ADDS a record's `amount` to `/totals["batch"]` when `amount` is a JSON **string** decimal (e.g. "19.99"). A JSON number:
- float (19.99) → accepted but NOT counted (totals stay 0.0)
- integer (1999) → counted literally as 1999 (no cents scaling)

So `submit_batch` in billing/client.py must serialize amounts with `str(r["amount"])`. `str()` forms like "5.0" and "0.01" parse fine server-side.

Probe recipe: `curl $MOCKPAY_URL/reset`, POST to `/batch`, then GET `/totals`. Top-level key must be `records` (not `items` → "bad request"). Fields `cents`/`value`/`amount_cents` are ignored.
