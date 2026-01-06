import json
import os
from datetime import datetime, timedelta

class FraudDetector:
    def __init__(self, config_path="fraud_config.json"):
        self.config = self._load_config(config_path)
        
    def _load_config(self, path):
        if not os.path.exists(path):
            # Fallback default configuration
            return {
                "high_risk_locations": ["HighRiskCountry", "Unknown"],
                "risky_merchants": ["GamblingSite", "CryptoExchange"],
                "amount_thresholds": {"low": 1000, "medium": 5000, "high": 10000},
                "velocity_rules": {"max_transactions_per_hour": 3, "max_amount_per_hour": 20000},
                "risk_weights": {
                    "amount_high": 50, "amount_medium": 30, "amount_low": 10,
                    "location": 40, "merchant": 30,
                    "velocity_count": 60, "velocity_amount": 50
                }
            }
        
        with open(path, 'r') as f:
            return json.load(f)

    def evaluate_risk(self, amount, location, merchant, transaction_history=None):
        """
        Evaluate transaction risk based on amount, location, merchant, and history.
        
        :param amount: Transaction amount
        :param location: Transaction location
        :param merchant: Merchant name
        :param transaction_history: List of dicts [{'amount': float, 'timestamp': datetime}, ...]
        """
        risk_score = 0
        reasons = []
        weights = self.config.get("risk_weights", {})

        # 1. Amount Check
        thresholds = self.config["amount_thresholds"]
        if amount > thresholds["high"]:
            risk_score += weights.get("amount_high", 50)
            reasons.append(f"Amount > {thresholds['high']}")
        elif amount > thresholds["medium"]:
            risk_score += weights.get("amount_medium", 30)
            reasons.append(f"Amount > {thresholds['medium']}")
        elif amount > thresholds["low"]:
            risk_score += weights.get("amount_low", 10)
            reasons.append(f"Amount > {thresholds['low']}")

        # 2. Location Check
        if location in self.config["high_risk_locations"]:
            risk_score += weights.get("location", 40)
            reasons.append(f"High risk location: {location}")

        # 3. Merchant Check
        if merchant in self.config["risky_merchants"]:
            risk_score += weights.get("merchant", 30)
            reasons.append(f"Risky merchant: {merchant}")

        # 4. Velocity Check (if history provided)
        if transaction_history:
            velocity_risk, velocity_reasons = self._check_velocity(amount, transaction_history)
            risk_score += velocity_risk
            reasons.extend(velocity_reasons)

        # Cap score at 100
        risk_score = min(risk_score, 100)

        # Determine Risk Level
        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reasons": reasons
        }

    def _check_velocity(self, current_amount, history):
        """
        Check transaction frequency and cumulative amount in the last hour.
        """
        risk = 0
        reasons = []
        rules = self.config["velocity_rules"]
        weights = self.config.get("risk_weights", {})
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        # Filter recent transactions
        recent_txns = [t for t in history if t['timestamp'] > one_hour_ago]
        
        # Count Check
        if len(recent_txns) >= rules["max_transactions_per_hour"]:
            risk += weights.get("velocity_count", 60)
            reasons.append(f"Velocity: > {rules['max_transactions_per_hour']} txns/hour")
            
        # Cumulative Amount Check
        total_recent_amount = sum(t['amount'] for t in recent_txns) + current_amount
        if total_recent_amount > rules["max_amount_per_hour"]:
            risk += weights.get("velocity_amount", 50)
            reasons.append(f"Velocity: > {rules['max_amount_per_hour']} amount/hour")
            
        return risk, reasons

# Example usage
if __name__ == "__main__":
    detector = FraudDetector()
    
    # Simulate history
    now = datetime.now()
    history = [
        {'amount': 5000, 'timestamp': now - timedelta(minutes=10)},
        {'amount': 5000, 'timestamp': now - timedelta(minutes=20)},
        {'amount': 5000, 'timestamp': now - timedelta(minutes=30)}
    ]
    
    # Test Velocity
    print("Testing Velocity Check:")
    print(detector.evaluate_risk(100, "US", "Amazon", history))
