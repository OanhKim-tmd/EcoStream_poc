"""Unit tests for deterministic mitigation math, GPT reduction, and quota compliance."""

import unittest
from ecostream.models.mitigation import MitigationMeasure, MitigationCategory
from ecostream.engine.mitigation_math import MitigationMathEngine


class TestMitigationMath(unittest.TestCase):
    def test_single_measure_gpt_calculation(self):
        m = MitigationMeasure(
            measure_id="MM-01",
            measure_name="Rooftop Solar PV 1.2 MWp",
            category=MitigationCategory.RENEWABLE_ENERGY,
            description="Install solar on factory roofs",
            baseline_emissions_ptcs=950.0,
            actual_emissions_pt=180.0,
            emission_reduction_gpt=0.0,  # will be computed
        )
        calculated = MitigationMathEngine.calculate_measure(m)
        self.assertEqual(calculated.emission_reduction_gpt, 770.0)
        self.assertEqual(calculated.reduction_pct, 81.05)

    def test_quota_surplus_calculation(self):
        profile = MitigationMathEngine.calculate_quota_profile(
            facility_id="FAC-01",
            facility_name="Nhà máy Nhiệt điện Phả Lại",
            allocated_quota_tonnes=5000.0,
            actual_inventory_tonnes=4200.0,
            mitigation_reductions_tonnes=800.0,
        )
        self.assertEqual(profile.quota_balance_tonnes, 800.0)
        self.assertIn("THẶNG DƯ", profile.compliance_status)

    def test_quota_deficit_calculation(self):
        profile = MitigationMathEngine.calculate_quota_profile(
            facility_id="FAC-01",
            facility_name="Nhà máy Nhiệt điện Mông Dương",
            allocated_quota_tonnes=3500.0,
            actual_inventory_tonnes=4200.0,
            mitigation_reductions_tonnes=200.0,
        )
        self.assertEqual(profile.quota_balance_tonnes, -700.0)
        self.assertIn("THIẾU HỤT", profile.compliance_status)

    def test_mitigation_summary_aggregation(self):
        measures = [
            MitigationMeasure(
                measure_id="MM-01",
                measure_name="Rooftop Solar 1.2 MWp",
                category=MitigationCategory.RENEWABLE_ENERGY,
                description="Solar PV",
                baseline_emissions_ptcs=950.0,
                actual_emissions_pt=180.0,
                emission_reduction_gpt=0.0,
            ),
            MitigationMeasure(
                measure_id="MM-02",
                measure_name="Biomass Co-firing 15%",
                category=MitigationCategory.FUEL_SWITCHING,
                description="Replace 15% coal with biomass pellets",
                baseline_emissions_ptcs=2400.0,
                actual_emissions_pt=1750.0,
                emission_reduction_gpt=0.0,
            ),
        ]
        summary = MitigationMathEngine.generate_mitigation_summary(
            facility_name="Cơ sở Công nghiệp A",
            measures=measures,
            allocated_quota_tonnes=4000.0,
            actual_inventory_tonnes=3600.0,
        )
        self.assertEqual(summary.total_baseline_ptcs, 3350.0)
        self.assertEqual(summary.total_actual_pt, 1930.0)
        self.assertEqual(summary.total_reduction_gpt, 1420.0)
        self.assertEqual(summary.overall_reduction_pct, 42.39)
        self.assertIsNotNone(summary.quota_profile)


if __name__ == "__main__":
    unittest.main()
