"""Curated emission factors database tailored for Vietnamese SMEs and international export compliance."""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from ecostream.models.activity import EmissionScope, ActivityCategory


class EmissionFactor(BaseModel):
    """Auditable emission factor specification."""
    factor_id: str
    name: str
    scope: EmissionScope
    category: ActivityCategory
    factor_value: float = Field(description="CO2e in kg per unit")
    unit: str = Field(description="Activity unit, e.g., kWh, liter, kg, ton-km, VND")
    source: str = Field(description="Official reference or publishing body")
    geography: str = Field(default="VN", description="Geographic specificity (VN, Global, EU)")
    year: int = Field(default=2023)
    default_uncertainty_pct: float = Field(default=10.0, description="Base uncertainty percentage (+/- %)")
    description: str


class EmissionFactorDatabase:
    """In-memory emission factor registry with fuzzy and exact key lookup."""

    def __init__(self):
        self._factors: Dict[str, EmissionFactor] = {}
        self._load_default_factors()

    def register(self, factor: EmissionFactor) -> None:
        self._factors[factor.factor_id] = factor

    def get(self, factor_id: str) -> Optional[EmissionFactor]:
        return self._factors.get(factor_id)

    def find_best_match(
        self,
        scope: EmissionScope,
        category: ActivityCategory,
        unit: str,
        query: str = "",
    ) -> Optional[EmissionFactor]:
        """Find the most appropriate emission factor based on scope, category, unit, and query text."""
        normalized_unit = unit.strip().lower()
        query_lower = query.lower()

        matches: List[EmissionFactor] = []
        for factor in self._factors.values():
            if factor.scope == scope and factor.unit.lower() == normalized_unit:
                matches.append(factor)

        if not matches:
            # Fallback across unit synonyms (e.g. kwh vs kwh, l vs liter, l vs lit)
            unit_map = {"l": "liter", "lít": "liter", "lit": "liter", "t.km": "ton-km", "tấn.km": "ton-km"}
            alt_unit = unit_map.get(normalized_unit, normalized_unit)
            for factor in self._factors.values():
                if factor.scope == scope and factor.unit.lower() == alt_unit:
                    matches.append(factor)

        if not matches:
            return None

        # Prefer Vietnam geography if available
        vn_matches = [m for m in matches if m.geography == "VN"]
        candidate_pool = vn_matches if vn_matches else matches

        # Specialized domain keyword mapping
        keyword_targets = {
            ("carton", "thùng", "giấy", "bao bì carton"): "EF-SCOPE3-CARTON",
            ("pe", "plastic", "nilon", "nhựa", "màng co"): "EF-SCOPE3-PLASTIC-FILM",
            ("cotton", "vải", "dệt", "textile", "sợi"): "EF-SCOPE3-COTTON-FABRIC",
            ("diesel", "điêzen", "dầu", "do 0.05"): "EF-SCOPE1-DIESEL",
            ("xăng", "gasoline", "petrol", "ron"): "EF-SCOPE1-PETROL",
            ("điện", "evn", "kwh", "grid"): "EF-SCOPE2-VN-GRID",
            ("vận chuyển", "freight", "xe tải", "truck"): "EF-SCOPE3-ROAD-FREIGHT-TK",
        }

        for k_words, target_id in keyword_targets.items():
            if any(kw in query_lower for kw in k_words):
                for cand in candidate_pool:
                    if cand.factor_id == target_id:
                        return cand

        # Fallback to general matches
        if query_lower:
            for cand in candidate_pool:
                cand_terms = cand.name.lower().replace("(", " ").replace(")", " ").split()
                if any(t in query_lower for t in cand_terms if len(t) > 3):
                    return cand

        return candidate_pool[0]

    def _load_default_factors(self) -> None:
        defaults = [
            # Scope 1 - Stationary & Mobile Combustion
            EmissionFactor(
                factor_id="EF-SCOPE1-DIESEL",
                name="Diesel Fuel Combustion (Dầu DO)",
                scope=EmissionScope.SCOPE_1,
                category=ActivityCategory.STATIONARY_COMBUSTION,
                factor_value=2.6800,
                unit="liter",
                source="IPCC Guidelines for National GHG Inventories (2006) / Vietnam Standard",
                geography="VN",
                year=2023,
                default_uncertainty_pct=7.5,
                description="Stationary boiler and backup generator diesel combustion.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE1-PETROL",
                name="Gasoline / Petrol Combustion (Xăng RON 95/E5)",
                scope=EmissionScope.SCOPE_1,
                category=ActivityCategory.MOBILE_COMBUSTION,
                factor_value=2.3100,
                unit="liter",
                source="IPCC Guidelines 2006 / GHG Protocol Mobile Guidance",
                geography="VN",
                year=2023,
                default_uncertainty_pct=8.0,
                description="Company-owned passenger and delivery vehicles.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE1-LPG",
                name="Liquefied Petroleum Gas (LPG Khí đốt)",
                scope=EmissionScope.SCOPE_1,
                category=ActivityCategory.STATIONARY_COMBUSTION,
                factor_value=2.9800,
                unit="kg",
                source="IPCC Guidelines 2006",
                geography="VN",
                year=2023,
                default_uncertainty_pct=10.0,
                description="Industrial heating, canteen, and thermal processes.",
            ),

            # Scope 2 - Purchased Electricity (Vietnam Grid)
            EmissionFactor(
                factor_id="EF-SCOPE2-VN-GRID",
                name="Vietnam National Electricity Grid Baseline (Lưới điện Quốc gia VN)",
                scope=EmissionScope.SCOPE_2,
                category=ActivityCategory.PURCHASED_ELECTRICITY,
                factor_value=0.7221,
                unit="kWh",
                source="Vietnam Ministry of Natural Resources & Environment (MONRE) - National Grid Factor 2022/2023",
                geography="VN",
                year=2023,
                default_uncertainty_pct=5.0,
                description="Official Vietnam power grid emission factor for commercial/industrial consumers.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE2-SOLAR-ROOFTOP",
                name="On-site Solar Photovoltaic (Điện mặt trời mái nhà)",
                scope=EmissionScope.SCOPE_2,
                category=ActivityCategory.PURCHASED_ELECTRICITY,
                factor_value=0.0000,
                unit="kWh",
                source="GHG Protocol Scope 2 Guidance (Market-based)",
                geography="VN",
                year=2023,
                default_uncertainty_pct=0.0,
                description="Self-generated zero-emission renewable electricity.",
            ),

            # Scope 3 - Upstream Transportation & Logistics
            EmissionFactor(
                factor_id="EF-SCOPE3-ROAD-FREIGHT-TK",
                name="Road Freight Transport (Vận chuyển đường bộ xe tải)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.UPSTREAM_TRANSPORTATION,
                factor_value=0.0960,
                unit="ton-km",
                source="GLEC Framework v3.0 / DEFRA 2023 Freight Standards",
                geography="VN",
                year=2023,
                default_uncertainty_pct=15.0,
                description="Medium & heavy diesel road freight in Southeast Asia.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE3-VAN-TK",
                name="Light Commercial Van Logistics (Xe tải nhỏ giao hàng)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.UPSTREAM_TRANSPORTATION,
                factor_value=0.2100,
                unit="ton-km",
                source="DEFRA 2023 / UK BEIS",
                geography="Global",
                year=2023,
                default_uncertainty_pct=18.0,
                description="Local distribution and parcel delivery.",
            ),

            # Scope 3 - Purchased Goods & Materials
            EmissionFactor(
                factor_id="EF-SCOPE3-CARTON",
                name="Corrugated Cardboard Packaging (Thùng carton đóng gói)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.PURCHASED_GOODS,
                factor_value=0.9400,
                unit="kg",
                source="DEFRA 2023 Material Factors",
                geography="Global",
                year=2023,
                default_uncertainty_pct=15.0,
                description="Recycled and virgin corrugated cardboard packaging.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE3-PLASTIC-FILM",
                name="LDPE Plastic Wrapping & Polybags (Túi bóng & màng co PE)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.PURCHASED_GOODS,
                factor_value=2.4500,
                unit="kg",
                source="PlasticsEurope / Ecoinvent 3.9",
                geography="Global",
                year=2023,
                default_uncertainty_pct=20.0,
                description="Polyethylene protective packaging for garments and goods.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE3-COTTON-FABRIC",
                name="Raw Cotton Textile Material (Vải Cotton thô)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.PURCHASED_GOODS,
                factor_value=8.3000,
                unit="kg",
                source="Higg Materials Sustainability Index (Higg MSI) / Textile Exchange",
                geography="Global",
                year=2023,
                default_uncertainty_pct=25.0,
                description="Cradle-to-gate cotton fabric production including spinning and weaving.",
            ),

            # Scope 3 - Spend-based Fallback Proxies
            EmissionFactor(
                factor_id="EF-SCOPE3-SPEND-LOGISTICS-VND",
                name="Spend-based Freight Proxy (Ước tính theo chi phí vận chuyển)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.UPSTREAM_TRANSPORTATION,
                factor_value=0.00025,  # kg CO2e per VND (0.25 kg per 1000 VND)
                unit="VND",
                source="EXIOBASE 3 Multi-Regional Input-Output Table (Vietnam Sector Proxy)",
                geography="VN",
                year=2022,
                default_uncertainty_pct=40.0,
                description="Macroeconomic spend-to-carbon proxy when physical ton-km data is unavailable.",
            ),
            EmissionFactor(
                factor_id="EF-SCOPE3-SPEND-MATERIALS-VND",
                name="Spend-based Material Proxy (Ước tính theo chi phí nguyên vật liệu)",
                scope=EmissionScope.SCOPE_3,
                category=ActivityCategory.PURCHASED_GOODS,
                factor_value=0.00038,  # kg CO2e per VND
                unit="VND",
                source="EXIOBASE 3 Input-Output Model",
                geography="VN",
                year=2022,
                default_uncertainty_pct=45.0,
                description="Spend-to-carbon fallback proxy for unclassified supplier procurement.",
            ),
        ]
        for f in defaults:
            self.register(f)


# Singleton factory
_global_db: Optional[EmissionFactorDatabase] = None

def get_factor_database() -> EmissionFactorDatabase:
    global _global_db
    if _global_db is None:
        _global_db = EmissionFactorDatabase()
    return _global_db
