import unittest
from datetime import datetime, timedelta
from fraud_detection import FraudDetector

class TestFraudDetector(unittest.TestCase):
    def setUp(self):
        # Initialize with default config file
        self.detector = FraudDetector("fraud_config.json")

    def test_low_risk_transaction(self):
        # Amount < 1000, Safe Location, Safe Merchant
        result = self.detector.evaluate_risk(500, "US", "Amazon")
        self.assertEqual(result["risk_level"], "LOW")
        self.assertEqual(result["risk_score"], 0)
        self.assertEqual(len(result["reasons"]), 0)

    def test_medium_amount_risk(self):
        # Amount > 1000 but < 5000
        result = self.detector.evaluate_risk(1500, "US", "Amazon")
        self.assertEqual(result["risk_score"], 10)
        self.assertEqual(result["risk_level"], "LOW") # 10 is LOW (<20)

    def test_high_amount_risk(self):
        # Amount > 10000
        result = self.detector.evaluate_risk(15000, "US", "Amazon")
        self.assertEqual(result["risk_score"], 50)
        self.assertIn("Amount > 10000", result["reasons"])
        self.assertEqual(result["risk_level"], "HIGH")

    def test_high_risk_location(self):
        result = self.detector.evaluate_risk(500, "HighRiskCountry", "Amazon")
        self.assertEqual(result["risk_score"], 40)
        self.assertIn("High risk location: HighRiskCountry", result["reasons"])
        self.assertEqual(result["risk_level"], "MEDIUM")

    def test_risky_merchant(self):
        result = self.detector.evaluate_risk(500, "US", "GamblingSite")
        self.assertEqual(result["risk_score"], 30)
        self.assertIn("Risky merchant: GamblingSite", result["reasons"])
        self.assertEqual(result["risk_level"], "MEDIUM")

    def test_critical_combination(self):
        # High amount + Risky Location + Risky Merchant
        # 50 + 40 + 30 = 120 -> Cap at 100
        result = self.detector.evaluate_risk(15000, "HighRiskCountry", "GamblingSite")
        self.assertEqual(result["risk_score"], 100)
        self.assertEqual(result["risk_level"], "CRITICAL")
        self.assertEqual(len(result["reasons"]), 3)

    def test_score_capping(self):
        # Ensure score never exceeds 100
        result = self.detector.evaluate_risk(100000, "HighRiskCountry", "GamblingSite")
        self.assertEqual(result["risk_score"], 100)

    def test_velocity_count_risk(self):
        # History has 3 txns in last hour (threshold is 3)
        now = datetime.now()
        history = [
            {'amount': 100, 'timestamp': now - timedelta(minutes=5)},
            {'amount': 100, 'timestamp': now - timedelta(minutes=15)},
            {'amount': 100, 'timestamp': now - timedelta(minutes=25)}
        ]
        # Current txn makes it 4
        result = self.detector.evaluate_risk(100, "US", "Amazon", history)
        
        # Expect velocity risk (60 points)
        self.assertGreaterEqual(result["risk_score"], 60)
        self.assertEqual(result["risk_level"], "HIGH") # 60 -> HIGH
        self.assertTrue(any("Velocity: > 3 txns/hour" in r for r in result["reasons"]))

    def test_velocity_amount_risk(self):
        # History has 18000 in last hour (threshold is 20000)
        now = datetime.now()
        history = [
            {'amount': 18000, 'timestamp': now - timedelta(minutes=10)}
        ]
        # Current txn of 3000 makes total 21000
        result = self.detector.evaluate_risk(3000, "US", "Amazon", history)
        
        # Expect velocity amount risk (50 points) + medium amount risk (10 points for > 1000)
        # Total 60
        self.assertGreaterEqual(result["risk_score"], 50)
        self.assertTrue(any("Velocity: > 20000 amount/hour" in r for r in result["reasons"]))

    def test_velocity_ignore_old_transactions(self):
        # History has txns older than 1 hour
        now = datetime.now()
        history = [
            {'amount': 5000, 'timestamp': now - timedelta(hours=2)},
            {'amount': 5000, 'timestamp': now - timedelta(hours=3)}
        ]
        # Current txn
        result = self.detector.evaluate_risk(100, "US", "Amazon", history)
        
        # Should be 0 risk
        self.assertEqual(result["risk_score"], 0)
        self.assertEqual(result["risk_level"], "LOW")

if __name__ == '__main__':
    unittest.main()
