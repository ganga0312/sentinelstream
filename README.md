# Fraud Detection System

A rule-based fraud detection microservice built with Python, FastAPI, and SQLite.

## Features

- **Rule-Based Scoring**: Evaluates transactions based on amount, location, and merchant.
- **Velocity Checks**: Automatically detects high-frequency or high-cumulative-amount transactions in the last hour.
- **Dynamic Configuration**: Thresholds and risk weights are stored in `fraud_config.json`.
- **Persistence**: Transactions are saved to a SQLite database (`fraud_detection.db`) for historical analysis.
- **Security**: API Key authentication (`X-API-Key`) required for evaluation requests.
- **Monitoring**: Built-in Admin Dashboard for real-time visualization of risk assessments.
- **Logging**: High-risk transactions are logged to `fraud_alerts.log`.
- **Container Ready**: Includes `Dockerfile` and `docker-compose.yml`.

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the API
```bash
uvicorn api:app --reload --port 8001
```

### 3. Usage
- **API Docs**: Access interactive documentation at `http://127.0.0.1:8001/docs`.
- **Dashboard**: Monitor transactions at `http://127.0.0.1:8001/dashboard` (or root `/`).

**Example Request:**
```bash
curl -X POST "http://127.0.0.1:8001/evaluate" \
     -H "X-API-Key: secret-fraud-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "transaction_id": "txn_123",
       "amount": 15000,
       "location": "HighRiskCountry",
       "merchant": "GamblingSite"
     }'
```

## Running on GitHub

### 1. GitHub Actions (CI)
The project includes a GitHub Actions workflow in `.github/workflows/test.yml`. It automatically:
- Installs dependencies.
- Runs unit tests.
- Starts the FastAPI server and runs integration tests.

### 2. GitHub Codespaces
You can run this project entirely in your browser using GitHub Codespaces:
1. Go to your GitHub repository.
2. Click the **Code** button and select the **Codespaces** tab.
3. Click **Create codespace on main**.
4. Once the environment loads, run the API using the command in step 2.

## Configuration

Update `fraud_config.json` to modify:
- `high_risk_locations`
- `risky_merchants`
- `amount_thresholds`
- `velocity_rules` (max transactions/amount per hour)
- `risk_weights` (how much score to add for each violation)

## Testing

Run unit tests:
```bash
python test_fraud_detection.py
```

Run integration tests (requires server to be running):
```bash
python test_integration.py
```

## Docker Deployment
```bash
docker compose up -d --build
```
*(Requires Docker to be installed)*
