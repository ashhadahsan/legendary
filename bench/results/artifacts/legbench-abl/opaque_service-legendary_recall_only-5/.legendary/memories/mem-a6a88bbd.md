---
id: mem-a6a88bbd
type: episode
title: MOCKPAY /batch only tallies `amount` when sent as a string
created: '2026-08-21T17:27:08.674950Z'
source: agent
status: active
anchors:
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 21
  commit: 930c2c7
  content_hash: sha256:7ad625d795d33d7208d9d723e9181121c662cb1b8afe7aad9a10aebcd6662a22
tags:
- billing
- mockpay
- opaque-service
triggers:
- test_billing_reconciliation
- server_totals()["batch"] == pytest.approx(25.00)
---
The payments service (MOCKPAY_URL) `/batch` endpoint silently drops any record whose `amount` is a JSON number — it returns `{"status":"accepted"}` but adds $0 to the batch total. It only tallies the amount when `amount` is a JSON **string** (e.g. "19.99"). Probed by resetting and posting variants; string form reconciled to 25.00 while numeric form gave 0.0.

Fix in `submit_batch`: serialize as `"amount": str(r["amount"])`. `str()` output like "5.0" parses fine server-side.

Endpoints: POST /batch, GET /totals -> {"batch","refund"}, GET/POST /reset. Field-name variants (amount_cents, cents, value, top-level type) were all ignored — only string `amount` works.
