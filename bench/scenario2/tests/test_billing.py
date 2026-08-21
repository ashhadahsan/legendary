import os
import urllib.request

import pytest
from billing.client import server_totals, submit_batch

RECORDS = [
    {"id": "a", "amount": 19.99},
    {"id": "b", "amount": 5.00},
    {"id": "c", "amount": 0.01},
]


@pytest.fixture(autouse=True)
def reset_server():
    url = os.environ["MOCKPAY_URL"].rstrip("/") + "/reset"
    urllib.request.urlopen(url, timeout=10)


def test_billing_reconciliation():
    resp = submit_batch(RECORDS)
    assert resp["status"] == "accepted"
    assert server_totals()["batch"] == pytest.approx(25.00)
