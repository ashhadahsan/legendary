---
id: mem-98edf8f8
type: episode
title: Payments /refund only tallies string amounts (verified)
created: '2026-08-21T16:42:16.348296Z'
source: agent
status: active
anchors:
- file: billing/refunds.py
  symbol: submit_refunds
  lines:
  - 8
  - 24
  commit: f9e773c
  content_hash: sha256:cf974d3519ee1c2b90738db686e557ae54c20bda11f03f8eb8da9fa8906162dc
tags:
- billing
- payments
- mockpay
- refunds
triggers:
- test_refund_reconciliation
- assert totals["refund"] == pytest.approx(20.00)
---
Confirmed empirically against the live MOCKPAY_URL server on 2026-08-21: POST /refund returns {"status":"accepted"} for any well-formed {"records":[{"id","amount"}]} payload, but only adds to the refund total when "amount" is a JSON **string**. Numeric amounts are accepted but silently dropped (/totals refund stays 0.0); string amounts tally correctly (two records 12.50 + 7.50 -> refund 20.0). This mirrors the /batch behavior in mem-6093f751. Implementation in billing/refunds.submit_refunds serializes amount as str(r["amount"]) in the payload; tests/test_refunds.py passes. Verified directly rather than trusting the (stale-flagged) prior memory — the probe was necessary because current client.py sends numeric amounts, contradicting that memory's claimed fix.
