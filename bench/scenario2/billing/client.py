"""Submit billing batches to the payments service (URL in MOCKPAY_URL)."""

import json
import os
import urllib.request


def submit_batch(records: list[dict]) -> dict:
    """POST records to /batch. Each record: {"id": str, "amount": <number>}."""
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/batch"
    payload = {"records": [{"id": r["id"], "amount": r["amount"]} for r in records]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def server_totals() -> dict:
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/totals"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())
