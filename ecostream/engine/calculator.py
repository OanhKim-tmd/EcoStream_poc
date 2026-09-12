"""Carbon accounting calculator with GHG Protocol Scope 1/2/3 categorization and uncertainty propagation."""

import math
from typing import List, Tuple
from ecostream.models.activity import ActivityRecord, EmissionScope, MeasurementType
from ecostream.models.results import CarbonCalculation, ScopeBreakdown
from ecostream.factors.database import EmissionFactorDatabase, get_factor_database


class CarbonCalculator:
    """Calculates CO2e footprint, analytical uncertainty bounds, and scope aggregations."""

    def __init__(self, db: EmissionFactorDatabase = None):
        self.db = db or get_factor_database()

    def calculate_single(self, record: ActivityRecord) -> CarbonCalculation:
        # Find factor
        factor = self.db.find_best_match(
            scope=record.scope,
            category=record.category,
            unit=record.unit,
            query=f"{record.description} {record.unit}",
        )

        if not factor:
            # Fallback conservative factor
            factor_val = 1.0
            factor_source = "Fallback Proxy Factor"
            factor_unit = record.unit
            uncertainty_base = 35.0
        else:
            factor_val = factor.factor_value
            factor_source = f"{factor.name} ({factor.source})"
            factor_unit = factor.unit
            uncertainty_base = factor.default_uncertainty_pct

        # CO2e calculation
        co2e_kg = record.quantity * factor_val
        co2e_tonnes = co2e_kg / 1000.0

        # Adjust uncertainty based on data quality and measurement tier
        uncertainty_pct = uncertainty_base
        if record.measurement_type == MeasurementType.SPEND_BASED_PROXY:
            uncertainty_pct = max(uncertainty_pct, 40.0)
        elif record.measurement_type == MeasurementType.PRIMARY_METERED:
            uncertainty_pct = min(uncertainty_pct, 5.0)

        # Penalty if completeness or temporal score is low
        if record.quality.completeness_score < 0.8:
            uncertainty_pct += 5.0

        uncertainty_min = max(0.0, co2e_tonnes * (1.0 - (uncertainty_pct / 100.0)))
        uncertainty_max = co2e_tonnes * (1.0 + (uncertainty_pct / 100.0))

        return CarbonCalculation(
            activity_id=record.id,
            description=record.description,
            scope=record.scope,
            category=record.category,
            activity_value=record.quantity,
            activity_unit=record.unit,
            emission_factor_value=factor_val,
            emission_factor_unit=factor_unit,
            emission_factor_source=factor_source,
            co2e_kg=round(co2e_kg, 2),
            co2e_tonnes=round(co2e_tonnes, 4),
            uncertainty_pct=round(uncertainty_pct, 1),
            uncertainty_min_tonnes=round(uncertainty_min, 4),
            uncertainty_max_tonnes=round(uncertainty_max, 4),
            quality_composite_score=round(record.quality.composite_score * 100.0, 1),
            evidence=record.evidence,
        )

    def calculate_all(self, records: List[ActivityRecord]) -> List[CarbonCalculation]:
        return [self.calculate_single(r) for r in records]

    def aggregate_scopes(self, calculations: List[CarbonCalculation]) -> Tuple[List[ScopeBreakdown], float, float, float]:
        """Aggregate totals and propagate combined analytical uncertainties across scopes."""
        total_tonnes = sum(c.co2e_tonnes for c in calculations)
        if total_tonnes == 0:
            total_tonnes = 0.0001

        breakdowns: List[ScopeBreakdown] = []
        scope_groups = {
            EmissionScope.SCOPE_1: [c for c in calculations if c.scope == EmissionScope.SCOPE_1],
            EmissionScope.SCOPE_2: [c for c in calculations if c.scope == EmissionScope.SCOPE_2],
            EmissionScope.SCOPE_3: [c for c in calculations if c.scope == EmissionScope.SCOPE_3],
        }

        # Root-sum-square total variance across all activities
        total_var_sum = 0.0

        for scope, items in scope_groups.items():
            scope_t = sum(i.co2e_tonnes for i in items)
            pct = round((scope_t / total_tonnes) * 100.0, 1)

            # RSS variance for this scope
            scope_var_sum = sum(((i.co2e_tonnes * (i.uncertainty_pct / 100.0)) ** 2) for i in items)
            total_var_sum += scope_var_sum
            scope_std = math.sqrt(scope_var_sum)

            avg_conf = (
                round(sum(i.quality_composite_score for i in items) / len(items), 1)
                if items
                else 100.0
            )

            breakdowns.append(
                ScopeBreakdown(
                    scope=scope,
                    total_tonnes=round(scope_t, 3),
                    percentage=pct,
                    uncertainty_lower_tonnes=round(max(0.0, scope_t - scope_std), 3),
                    uncertainty_upper_tonnes=round(scope_t + scope_std, 3),
                    activity_count=len(items),
                    avg_confidence_pct=avg_conf,
                )
            )

        total_std = math.sqrt(total_var_sum)
        total_min = round(max(0.0, total_tonnes - total_std), 3)
        total_max = round(total_tonnes + total_std, 3)

        return breakdowns, round(total_tonnes, 3), total_min, total_max
