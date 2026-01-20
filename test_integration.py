import os
import json
import uuid
import requests
import pytest

# Configuration
API_URL = "http://127.0.0.1:8001/evaluate"
API_KEY = "secret-fraud-api-key"
HEADERS = {"X-API-Key": API_KEY}

# Skip integration tests by default to avoid failures when the service isn't running.
skip_integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "2",
    reason="Integration tests are disabled. Set RUN_INTEGRATION=1 to enable."
)


@skip_integration
def test_low_risk_transaction():
    safe_id = f"txn_safe_{uuid.uuid4().hex[:6]}"
    payload = {
        "transaction_id": safe_id,
        "amount": 500,
        "location": "US",
        "merchant": "Amazon"
    }
    resp = requests.post(API_URL, json=payload, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("transaction_id") == safe_id


@skip_integration
def test_high_risk_transaction():
    risky_id = f"txn_risky_{uuid.uuid4().hex[:6]}"
    payload = {
        "transaction_id": risky_id,
        "amount": 15000,
        "location": "HighRiskCountry",
        "merchant": "GamblingSite"
    }
    resp = requests.post(API_URL, json=payload, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("transaction_id") == risky_id


@skip_integration
def test_unauthorized_access():
    payload = {
        "transaction_id": f"unauth_{uuid.uuid4().hex[:6]}",
        "amount": 100,
        "location": "US",
        "merchant": "Amazon"
    }
    resp = requests.post(API_URL, json=payload, headers={})
    assert resp.status_code in (401, 403)


@skip_integration
def test_get_request_help():
    resp = requests.get(API_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
