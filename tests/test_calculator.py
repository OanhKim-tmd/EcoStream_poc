"""Tests for emission calculations and uncertainty propagation."""

import unittest
from ecostream.models.activity import (
    ActivityRecord,
    EmissionScope,
    ActivityCategory,
    MeasurementType,
    EvidenceProvenance,
    DataQualityIndicator,
)
from ecostream.factors.database import get_factor_database
from ecostream.engine.calculator import CarbonCalculator


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.db = get_factor_database()
        self.calculator = CarbonCalculator(self.db)

    def test_scope2_evn_electricity_calculation(self):
        # 10,000 kWh * 0.7221 kg CO2/kWh = 7,221 kg CO2e = 7.221 tonnes
        rec = ActivityRecord(
            id="TEST-EVN",
            description="EVN Grid Power",
            scope=EmissionScope.SCOPE_2,
            category=ActivityCategory.PURCHASED_ELECTRICITY,
            quantity=10000.0,
            unit="kWh",
            measurement_type=MeasurementType.PRIMARY_METERED,
            evidence=EvidenceProvenance(
                source_document="test.txt",
                document_type="EVN",
                snippet="10000 kWh",
            ),
            quality=DataQualityIndicator(
                completeness_score=1.0,
                temporal_score=1.0,
                geographical_score=1.0,
                source_reliability_score=1.0,
                extraction_confidence_score=1.0,
            ),
        )
        calc = self.calculator.calculate_single(rec)
        self.assertAlmostEqual(calc.co2e_tonnes, 7.221, places=3)
        self.assertEqual(calc.scope, EmissionScope.SCOPE_2)
        self.assertLessEqual(calc.uncertainty_pct, 5.0)

    def test_scope1_diesel_calculation(self):
        # 1000 L * 2.68 kg CO2/L = 2,680 kg = 2.68 tonnes
        rec = ActivityRecord(
            id="TEST-DIESEL",
            description="Diesel Fuel DO 0.05S",
            scope=EmissionScope.SCOPE_1,
            category=ActivityCategory.STATIONARY_COMBUSTION,
            quantity=1000.0,
            unit="liter",
            measurement_type=MeasurementType.PRIMARY_INVOICED,
            evidence=EvidenceProvenance(
                source_document="fuel.txt",
                document_type="FUEL",
                snippet="1000 L",
            ),
            quality=DataQualityIndicator(
                completeness_score=1.0,
                temporal_score=1.0,
                geographical_score=1.0,
                source_reliability_score=0.95,
                extraction_confidence_score=0.96,
            ),
        )
        calc = self.calculator.calculate_single(rec)
        self.assertAlmostEqual(calc.co2e_tonnes, 2.68, places=2)

    def test_scope3_spend_proxy_uncertainty(self):
        # Spend proxy must have high uncertainty (+/- 40% or higher)
        rec = ActivityRecord(
            id="TEST-SPEND",
            description="Logistics spend proxy",
            scope=EmissionScope.SCOPE_3,
            category=ActivityCategory.UPSTREAM_TRANSPORTATION,
            quantity=10000000.0,
            unit="VND",
            measurement_type=MeasurementType.SPEND_BASED_PROXY,
            evidence=EvidenceProvenance(
                source_document="spend.csv",
                document_type="SPEND",
                snippet="10000000 VND",
            ),
            quality=DataQualityIndicator(
                completeness_score=0.6,
                temporal_score=0.9,
                geographical_score=0.8,
                source_reliability_score=0.4,
                extraction_confidence_score=0.9,
            ),
        )
        calc = self.calculator.calculate_single(rec)
        self.assertGreaterEqual(calc.uncertainty_pct, 40.0)


if __name__ == "__main__":
    unittest.main()
