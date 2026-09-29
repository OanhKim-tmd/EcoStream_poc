"""Unit tests for Query Log, Assumption Log, and reliability penalty mechanics."""

import unittest
from ecostream.agents.base import AgentContext
from ecostream.agents.scope1 import Scope1FuelAgent
from ecostream.agents.scope2 import Scope2PowerAgent
from ecostream.agents.scope3 import Scope3SupplyAgent
from ecostream.models.state import QueryStatus, AnomalyType
from ecostream.engine.reliability import ReliabilityEngine


class TestQueryAssumptionLogs(unittest.TestCase):
    def setUp(self):
        self.context = AgentContext(
            run_id="test-run-logs-01",
            company_name="EcoGarment VN",
            raw_markdown_sources={
                "fuels.md": "| Gas | Qty |\n| 50 bình LPG 12kg | 50 bình |",
                "evn.md": "| Month | kWh |\n| Tháng 06 | 50,000 |\n| Tháng 08 | 60,000 |",
                "spend.md": "| Item | Amount |\n| Mua ngoài | 45,000,000 VND |",
            },
            offline_mode=True,
        )

    def test_lpg_packaging_query_and_assumption(self):
        agent = Scope1FuelAgent()
        out = agent.run(self.context)
        self.assertEqual(len(out.queries), 1)
        self.assertEqual(len(out.assumptions), 1)
        q = out.queries[0]
        a = out.assumptions[0]

        self.assertEqual(q.anomaly_type, AnomalyType.UNIT_AMBIGUITY)
        self.assertEqual(q.status, QueryStatus.AUTO_ASSUMED)
        self.assertEqual(a.related_query_id, q.query_id)
        self.assertEqual(a.assumed_value, 600.0)
        self.assertEqual(a.assumed_unit, "kg")

    def test_evn_seasonal_gap_query_and_assumption(self):
        # Provide month 6 and 8, missing month 7
        agent = Scope2PowerAgent()
        out = agent.run(self.context)
        q = next((q for q in out.queries if q.anomaly_type == AnomalyType.SEASONAL_GAP), None)
        self.assertIsNotNone(q)
        self.assertIn("Tháng 07", q.detected_issue)

        a = next((a for a in out.assumptions if "Month 07" in a.parameter_name), None)
        self.assertIsNotNone(a)
        self.assertEqual(a.assumed_value, 55000.0)

    def test_spend_proxy_query_and_penalty(self):
        agent = Scope3SupplyAgent()
        out = agent.run(self.context)
        q = next((q for q in out.queries if q.anomaly_type == AnomalyType.SPEND_PROXY), None)
        self.assertIsNotNone(q)
        self.assertIn("45,000,000", q.detected_issue)

        # Evaluate reliability with assumption penalty
        rel = ReliabilityEngine.evaluate(out.records, assumption_penalty=5.0)
        self.assertLess(rel.overall_confidence_score, 80.0)


if __name__ == "__main__":
    unittest.main()
