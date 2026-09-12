"""Tests for ReliabilityEngine and 5-dimension scoring."""

import unittest
from ecostream.models.activity import (
    ActivityRecord,
    EmissionScope,
    ActivityCategory,
    MeasurementType,
    EvidenceProvenance,
    DataQualityIndicator,
)
from ecostream.engine.reliability import ReliabilityEngine


class TestReliability(unittest.TestCase):
    def test_high_quality_assessment(self):
        records = [
            ActivityRecord(
                id="ACT-1",
                description="EVN bill",
                scope=EmissionScope.SCOPE_2,
                category=ActivityCategory.PURCHASED_ELECTRICITY,
                quantity=5000,
                unit="kWh",
                measurement_type=MeasurementType.PRIMARY_METERED,
                evidence=EvidenceProvenance(source_document="f.txt", document_type="EVN", snippet="snip"),
                quality=DataQualityIndicator(
                    completeness_score=1.0,
                    temporal_score=1.0,
                    geographical_score=1.0,
                    source_reliability_score=1.0,
                    extraction_confidence_score=1.0,
                ),
            )
        ]
        res = ReliabilityEngine.evaluate(records)
        self.assertGreaterEqual(res.overall_confidence_score, 95.0)
        self.assertEqual(res.grade, "A")
        self.assertEqual(res.primary_data_ratio_pct, 100.0)
        self.assertEqual(res.spend_based_ratio_pct, 0.0)

    def test_low_quality_spend_proxy_assessment(self):
        records = [
            ActivityRecord(
                id="ACT-SPEND",
                description="Spend item",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.PURCHASED_GOODS,
                quantity=5000000,
                unit="VND",
                measurement_type=MeasurementType.SPEND_BASED_PROXY,
                evidence=EvidenceProvenance(source_document="f.txt", document_type="SPEND", snippet="snip"),
                quality=DataQualityIndicator(
                    completeness_score=0.4,
                    temporal_score=0.5,
                    geographical_score=0.5,
                    source_reliability_score=0.3,
                    extraction_confidence_score=0.6,
                ),
            )
        ]
        res = ReliabilityEngine.evaluate(records)
        self.assertLess(res.overall_confidence_score, 60.0)
        self.assertIn(res.grade, ["C", "D"])
        self.assertEqual(res.spend_based_ratio_pct, 100.0)


if __name__ == "__main__":
    unittest.main()
