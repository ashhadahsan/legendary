import json
import os
import urllib.request

import pytest
from billing.refunds import submit_refunds

RECORDS = [{"id": "r1", "amount": 12.50}, {"id": "r2", "amount": 7.50}]


@pytest.fixture(autouse=True)
def reset_server():
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/reset"
    urllib.request.urlopen(url, timeout=10)


def test_refund_reconciliation():
    resp = submit_refunds(RECORDS)
    assert resp["status"] == "accepted"
    totals = json.loads(
        urllib.request.urlopen(
            os.environ["MOCKPAY_URL"].rstrip("/") + "/totals", timeout=10
        ).read()
    )
    assert totals["refund"] == pytest.approx(20.00)
