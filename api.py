import logging
import os
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader, APIKey
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fraud_detection import FraudDetector
from database import init_db, get_db, Transaction

# Configure Logging
logging.basicConfig(
    filename='fraud_alerts.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Key Security
API_KEY_NAME = "X-API-Key"
API_KEY = "secret-fraud-api-key" # In production, load this from environment variables
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=403,
        detail="Could not validate credentials"
    )

app = FastAPI(title="Fraud Detection API")

# Add CORS Support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = FraudDetector()
templates = Jinja2Templates(directory="templates")

# Initialize Database on Startup
@app.on_event("startup")
def on_startup():
    init_db()

# Pydantic Models
class TransactionRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique ID of the transaction")
    amount: float = Field(..., gt=0, description="Transaction amount")
    location: str = Field(..., description="Location code (e.g., US, UK)")
    merchant: str = Field(..., description="Merchant name")

class RiskAssessment(BaseModel):
    transaction_id: str
    risk_score: int
    risk_level: str
    reasons: List[str]
    timestamp: datetime

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/evaluate")
async def evaluate_help():
    return {
        "message": "This endpoint expects a POST request with transaction data.",
        "example_payload": {
            "transaction_id": "txn_123",
            "amount": 1000,
            "location": "US",
            "merchant": "Amazon"
        }
    }

@app.post("/evaluate", response_model=RiskAssessment)
async def evaluate_transaction(
    request: TransactionRequest, 
    db: Session = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    try:
        # 1. Fetch recent history from DB for Velocity Checks
        # Get transactions from the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_txns = db.query(Transaction).filter(
            Transaction.timestamp >= one_hour_ago
        ).all()
        
        # Convert DB models to list of dicts for the detector
        history_dicts = [
            {'amount': t.amount, 'timestamp': t.timestamp} 
            for t in recent_txns
        ]

        # 2. Evaluate Risk
        result = detector.evaluate_risk(
            amount=request.amount,
            location=request.location,
            merchant=request.merchant,
            transaction_history=history_dicts
        )

        # 3. Log High Risk Transactions
        if result["risk_score"] >= 50:
            logger.warning(
                f"High Risk Transaction Detected! ID: {request.transaction_id}, "
                f"Score: {result['risk_score']}, Reasons: {result['reasons']}"
            )

        # 4. Save current transaction to DB
        # Only save if not already exists (basic idempotency)
        existing_txn = db.query(Transaction).filter(Transaction.transaction_id == request.transaction_id).first()
        if not existing_txn:
            new_txn = Transaction(
                transaction_id=request.transaction_id,
                amount=request.amount,
                location=request.location,
                merchant=request.merchant,
                timestamp=datetime.utcnow()
            )
            db.add(new_txn)
            db.commit()

        return RiskAssessment(
            transaction_id=request.transaction_id,
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            reasons=result["reasons"],
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error processing transaction {request.transaction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # Fetch recent transactions from the database
    transactions = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(50).all()
    
    # Enrich and calculate statistics
    enriched_txns = []
    stats = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    loc_stats = {}
    merch_stats = {}
    total_amount = 0
    
    for t in transactions:
        res = detector.evaluate_risk(t.amount, t.location, t.merchant)
        level = res["risk_level"]
        stats[level] += 1
        total_amount += t.amount
        
        # Location distribution
        loc_stats[t.location] = loc_stats.get(t.location, 0) + 1
        # Merchant distribution
        merch_stats[t.merchant] = merch_stats.get(t.merchant, 0) + 1
        
        enriched_txns.append({
            "timestamp": t.timestamp.isoformat(),
            "transaction_id": t.transaction_id,
            "amount": t.amount,
            "location": t.location,
            "merchant": t.merchant,
            "risk_score": res["risk_score"],
            "risk_level": level,
            "reasons": res["reasons"]
        })
    
    summary = {
        "total_count": len(transactions),
        "avg_amount": total_amount / len(transactions) if transactions else 0,
        "critical_count": stats["CRITICAL"],
        "distribution": stats,
        "location_distribution": loc_stats,
        "merchant_distribution": merch_stats,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "transactions": enriched_txns[:20], # Show only last 20 in table
        "summary": summary
    })

@app.get("/web", response_class=HTMLResponse)
async def web_interface(request: Request):
    return templates.TemplateResponse("evaluate.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Handle Vite ghost requests to clean up logs
@app.get("/favicon.ico")
@app.get("/@vite/client")
@app.get("/@fs/{path:path}")
async def vite_client(path: Optional[str] = None):
    return ""

@app.exception_handler(404)
async def custom_404_handler(request: Request, __):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
