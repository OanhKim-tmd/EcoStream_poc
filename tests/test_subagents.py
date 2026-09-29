"""Unit tests for domain subagents execution and extraction logic."""

import unittest
from ecostream.agents.base import AgentContext
from ecostream.agents.discovery import SchemaDiscoveryAgent
from ecostream.agents.scope1 import Scope1FuelAgent
from ecostream.agents.scope2 import Scope2PowerAgent
from ecostream.agents.scope3 import Scope3SupplyAgent
from ecostream.agents.mitigation import MitigationQuotaAgent
from ecostream.agents.synthesizer import ReportSynthesizerAgent


class TestSubagents(unittest.TestCase):
    def setUp(self):
        self.context = AgentContext(
            run_id="test-run-001",
            company_name="Test Garment JSC",
            facility_name="Test Factory Ha Nam",
            reporting_year=2026,
            raw_markdown_sources={
                "input_sheet_fuels.md": "| Item | Unit | Qty |\n| Dầu DO 0.05S | lít | 1850 |\n| 50 bình LPG 12kg | bình | 50 |",
                "input_sheet_evn.md": "| Month | kWh |\n| Tháng 01 | 45,000 |\n| Tháng 02 | 42,000 |\n| Tháng 03 | 48,000 |\n| Tháng 04 | 44,000 |\n| Tháng 05 | 50,000 |\n| Tháng 06 | 55,000 |\n| Tháng 08 | 58,000 |\n| Tháng 09 | 49,000 |\n| Tháng 10 | 46,000 |\n| Tháng 11 | 43,000 |\n| Tháng 12 | 47,000 |",
                "input_sheet_logistics.md": "| Route | Tonnes | Distance_km |\n| Hải Phòng - Hà Nam | 20 tấn | 120 km |\n| Spend Unclassified | VND | 25,000,000 |",
                "input_sheet_mitigation.md": "| Measure | Baseline PTCS | Actual PT |\n| Rooftop Solar 1.2 MWp | 950.0 | 180.0 |\n| Biomass Co-firing 15% | 2400.0 | 1750.0 |",
            },
            offline_mode=True,
        )

    def test_schema_discovery_agent(self):
        agent = SchemaDiscoveryAgent()
        out = agent.run(self.context)
        self.assertIn("index", out.extra_data)
        tasks = out.extra_data["index"]["tasks"]
        self.assertGreaterEqual(len(tasks), 3)
        agent_names = [t["target_agent"] for t in tasks]
        self.assertIn("Scope1FuelAgent", agent_names)
        self.assertIn("Scope2PowerAgent", agent_names)
        self.assertIn("Scope3SupplyAgent", agent_names)

    def test_scope1_fuel_agent(self):
        agent = Scope1FuelAgent()
        out = agent.run(self.context)
        self.assertGreaterEqual(len(out.records), 2)
        # Check LPG conversion: 50 * 12 = 600 kg
        lpg_rec = next((r for r in out.records if "LPG" in r.description), None)
        self.assertIsNotNone(lpg_rec)
        self.assertEqual(lpg_rec.quantity, 600.0)
        self.assertEqual(lpg_rec.unit, "kg")
        # Check queries and assumptions
        self.assertGreaterEqual(len(out.queries), 1)
        self.assertGreaterEqual(len(out.assumptions), 1)

    def test_scope2_power_agent_gap_detection(self):
        agent = Scope2PowerAgent()
        out = agent.run(self.context)
        # Months 1-6 and 8-12 exist, Month 7 was missing and interpolated
        self.assertEqual(len(out.records), 12)
        # Check Month 7 interpolated record: (55000 + 58000) / 2 = 56500
        m7_rec = next((r for r in out.records if "Tháng 07" in r.description), None)
        self.assertIsNotNone(m7_rec)
        self.assertEqual(m7_rec.quantity, 56500.0)
        # Verify query and assumption for Month 7 gap
        self.assertGreaterEqual(len(out.queries), 1)
        self.assertIn("Tháng 07", out.queries[0].detected_issue)

    def test_scope3_supply_agent(self):
        agent = Scope3SupplyAgent()
        out = agent.run(self.context)
        self.assertGreaterEqual(len(out.records), 2)
        # Check logistics t.km: 20 * 120 = 2400
        freight_rec = next((r for r in out.records if r.unit == "ton-km"), None)
        self.assertIsNotNone(freight_rec)
        self.assertEqual(freight_rec.quantity, 2400.0)
        # Check spend proxy
        spend_rec = next((r for r in out.records if r.unit == "VND"), None)
        self.assertIsNotNone(spend_rec)
        self.assertEqual(spend_rec.quantity, 25000000.0)

    def test_mitigation_quota_agent(self):
        agent = MitigationQuotaAgent()
        out = agent.run(self.context)
        self.assertIn("mitigation_summary", out.extra_data)
        summary = out.extra_data["mitigation_summary"]
        self.assertEqual(len(summary["measures"]), 2)
        self.assertEqual(summary["total_baseline_ptcs"], 3350.0)
        self.assertEqual(summary["total_actual_pt"], 1930.0)
        self.assertEqual(summary["total_reduction_gpt"], 1420.0)

    def test_synthesizer_agent(self):
        agent = ReportSynthesizerAgent()
        out = agent.run(self.context)
        self.assertIn("executive_summary_vn", out.extra_data)
        self.assertIn("mitigation_narrative_vn", out.extra_data)
        self.assertIn("ISO 14064-1", out.extra_data["executive_summary_vn"])


if __name__ == "__main__":
    unittest.main()
