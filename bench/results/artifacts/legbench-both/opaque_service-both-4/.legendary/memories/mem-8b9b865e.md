---
id: mem-8b9b865e
type: decision
title: MOCKPAY service silently drops float amounts; send string decimals
created: '2026-08-21T15:58:45.196053Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 13
  - 26
  commit: d53aa05
  content_hash: sha256:aee72aac97a0bcc119e186fd0d4b2e86fac3077b57b5f5cd817a734bff035b9d
- file: billing/client.py
  symbol: submit_batch
  lines:
  - 8
  - 19
  commit: d53aa05
  content_hash: sha256:77288785d24bdc4e0969feb00fc636764042c8d77d0c44589cf2ae1b7ee397a4
tags:
- billing
- mockpay
- payments
triggers: []
---
The payments service (MOCKPAY_URL, source /Users/ashhad/legendary/bench/mockpay.py) has a quirk modeled on real payment APIs: on POST /batch and POST /refund, any record whose `amount` is a JSON float is SILENTLY DROPPED — the response is still 200 {"status": "accepted"} but the amount is never added to /totals. Amounts MUST be serialized as string decimals (e.g. "12.50") to reconcile. Payload must be {"records":[{"id":..,"amount":".."}]} — any other top-level key returns {"status":"bad request"}. billing/refunds.py::submit_refunds sends str(amount). NOTE: billing/client.py::submit_batch sends raw floats and would ALSO be silently dropped — test_billing only reconciles if callers pass string amounts. Endpoints: GET /totals, GET /reset (both GET).
