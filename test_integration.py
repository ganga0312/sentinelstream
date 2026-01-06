import requests
import json
import uuid

# Configuration
API_URL = "http://127.0.0.1:8001/evaluate"
API_KEY = "secret-fraud-api-key"
HEADERS = {"X-API-Key": API_KEY}

def test_transaction(name, payload, headers=None):
    print(f"\n--- Testing {name} ---")
    try:
        if headers is None:
            headers = HEADERS
        response = requests.post(API_URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("Error Response:")
            print(response.text)
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    # Generate unique IDs to avoid DB collisions in repeated tests
    safe_id = f"txn_safe_{uuid.uuid4().hex[:6]}"
    risky_id = f"txn_risky_{uuid.uuid4().hex[:6]}"

    # 1. Low Risk Transaction
    test_transaction("Low Risk", {
        "transaction_id": safe_id,
        "amount": 500,
        "location": "US",
        "merchant": "Amazon"
    })

    # 2. High Risk Transaction
    test_transaction("Critical Risk", {
        "transaction_id": risky_id,
        "amount": 15000,
        "location": "HighRiskCountry",
        "merchant": "GamblingSite"
    })
    
    # 3. Test Unauthorized Access
    print(f"\n--- Testing Unauthorized Access ---")
    test_transaction("No API Key", {
        "transaction_id": "unauth_txn",
        "amount": 100,
        "location": "US",
        "merchant": "Amazon"
    }, headers={})

    # 4. GET Request Check (Instructions)
    print(f"\n--- Testing GET Request (Help) ---")
    try:
        response = requests.get(API_URL)
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(e)
