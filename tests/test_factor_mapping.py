"""Fuels without their own emission factor must never borrow another fuel's factor."""
import unittest

from ecostream.ingestion.survey_workbook import SurveyData, SurveyItem
from ecostream.orchestrator.survey_pipeline import FACTOR_IDS, _records, _uncalculated_warnings


def _item(kind, qty=1000.0, unit="kg", sheet="1.1"):
    return SurveyItem(kind=kind, month=1, quantity=qty, unit=unit, source_document="t.xlsx",
                      source_location="t", sheet=sheet, coordinate="F4")


class FactorMappingTests(unittest.TestCase):
    def test_biomass_and_waste_are_not_calculated_with_coal_factor(self):
        data = SurveyData(items=[_item("bituminous"), _item("rice_husk"), _item("municipal_waste")])
        records = _records(data, 2026)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].quantity, 1000.0)
        warnings = _uncalculated_warnings(data)
        self.assertEqual(len(warnings), 2)
        self.assertTrue(any("Trấu" in w and "sinh khối" in w for w in warnings))
        self.assertTrue(all("CHƯA TÍNH" in w for w in warnings))

    def test_only_fuels_with_dedicated_factor_are_mapped(self):
        for kind in ("wood", "bagasse", "biogas", "lng", "kerosene", "peat", "other_petroleum"):
            self.assertNotIn(kind, FACTOR_IDS)


if __name__ == "__main__":
    unittest.main()
