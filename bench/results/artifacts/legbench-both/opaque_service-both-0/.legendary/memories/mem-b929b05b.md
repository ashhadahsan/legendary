---
id: mem-b929b05b
type: decision
title: MOCKPAY opaque service only tallies string amounts, drops JSON floats
created: '2026-08-21T15:43:18.640038Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 26
  commit: cc6ad9c
  content_hash: sha256:2b4864249034180808910beb955517e233c68abe318f732bd467d92e1b835e11
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 19
  commit: cc6ad9c
  content_hash: sha256:77288785d24bdc4e0969feb00fc636764042c8d77d0c44589cf2ae1b7ee397a4
tags:
- mockpay
- opaque-service
- billing
triggers: []
---
The opaque MOCKPAY payments service (URL in MOCKPAY_URL) silently DROPS record amounts sent as JSON floats on both /refund and /batch — the POST returns {"status":"accepted"} but /totals stays 0.0. It only tallies amounts sent as JSON strings (e.g. "12.50") or ints. Discovered by probing with curl (reset -> POST -> totals). billing/refunds.py::submit_refunds therefore serializes each amount with str(r["amount"]) and passed tests/test_refunds.py. NOTE: billing/client.py::submit_batch sends raw floats, so tests/test_billing.py currently FAILS (batch total 0.0 vs expected 25.00) — same fix (string amounts) would apply, but was out of scope for the refunds-only task.
