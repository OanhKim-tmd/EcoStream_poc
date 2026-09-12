"""Specialized rule-based parsers for Vietnamese commercial utility bills, fuel invoices, and logistics sheets."""

import csv
import io
import re
from typing import List, Optional
from ecostream.ingestion.loaders import IngestedDocument
from ecostream.models.activity import (
    ActivityRecord,
    EmissionScope,
    ActivityCategory,
    MeasurementType,
    EvidenceProvenance,
    DataQualityIndicator,
)


def clean_num(val_str: str) -> float:
    """Parse Vietnamese and international number strings (e.g., '45.250', '1,850.50', '39 000')."""
    s = val_str.strip().replace(" ", "")
    # If both '.' and ',' are present, figure out which is decimal
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):  # European / VN format: 1.250,50
            s = s.replace(".", "").replace(",", ".")
        else:  # Standard US format: 1,250.50
            s = s.replace(",", "")
    elif "," in s:
        # Check if comma is decimal (e.g. 1,5 or 1850,00) or thousand separator
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        # If last part is 3 digits, it's often VN thousand separator e.g. 45.250
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")
    return float(s)


class EVNBillParser:
    """Parses electricity bills from Vietnam Electricity (EVN)."""

    @classmethod
    def can_parse(cls, doc: IngestedDocument) -> bool:
        c = doc.content.lower()
        return ("điện lực" in c or "evn" in c or "tiền điện" in c or "kwh" in c) and ("sản lượng" in c or "chỉ số" in c or "điện năng" in c)

    @classmethod
    def parse(cls, doc: IngestedDocument) -> List[ActivityRecord]:
        records: List[ActivityRecord] = []
        content = doc.content
        lines = content.splitlines()

        # Extract period
        period_match = re.search(r"Kỳ(?:\s+hóa\s+đơn)?[:\s]+(\d{1,2}/\d{4})", content, re.IGNORECASE)
        period = period_match.group(1) if period_match else "03/2026"

        # Look for customer and supplier
        supplier_match = re.search(r"(TỔNG\s+CÔNG\s+TY\s+ĐIỆN\s+LỰC[^\n\r]+|CÔNG\s+TY\s+ĐIỆN\s+LỰC[^\n\r]+|EVN[^\n\r]+)", content, re.IGNORECASE)
        supplier = supplier_match.group(1).strip() if supplier_match else "EVN (Vietnam Electricity)"

        # Search for total kWh or specific tariff tiers
        # Pattern: Tổng điện năng tiêu thụ: 45,250 kWh
        tot_kwh_match = re.search(
            r"(?:Tổng\s+điện\s+năng(?:\s+tiêu\s+thụ)?|Sản\s+lượng\s+(?:điện\s+)?tiêu\s+thụ|Tổng\s+kWh)[:\s]+([\d\.,\s]+)\s*(?:kWh|kw\.h)?",
            content,
            re.IGNORECASE,
        )

        cost_match = re.search(
            r"(?:Tổng\s+cộng\s+tiền\s+thanh\s+toán|Tổng\s+tiền|Thành\s+tiền)[:\s]+([\d\.,\s]+)\s*(?:đồng|vnđ|vnd)?",
            content,
            re.IGNORECASE,
        )
        cost_vnd = clean_num(cost_match.group(1)) if cost_match else None

        if tot_kwh_match:
            raw_val = tot_kwh_match.group(1).strip()
            try:
                kwh_value = clean_num(raw_val)
                matched_line = ""
                for line in lines:
                    if "tổng điện năng" in line.lower() or "sản lượng" in line.lower():
                        matched_line = line.strip()
                        break

                record = ActivityRecord(
                    id=f"ACT-EVN-{len(records)+1}",
                    description=f"EVN Grid Electricity Consumption (Kỳ {period})",
                    scope=EmissionScope.SCOPE_2,
                    category=ActivityCategory.PURCHASED_ELECTRICITY,
                    quantity=kwh_value,
                    unit="kWh",
                    date=period,
                    supplier=supplier,
                    cost_vnd=cost_vnd,
                    measurement_type=MeasurementType.PRIMARY_METERED,
                    evidence=EvidenceProvenance(
                        source_document=doc.filename,
                        document_type="EVN_BILL",
                        page_or_line=matched_line or f"EVN Bill {period}",
                        snippet=matched_line or f"Sản lượng điện tiêu thụ: {raw_val} kWh",
                        extraction_method="RULE_BASED_EVN",
                        extraction_confidence=0.98,
                    ),
                    quality=DataQualityIndicator(
                        completeness_score=1.0,
                        temporal_score=1.0,
                        geographical_score=1.0,  # Matches Vietnam national grid
                        source_reliability_score=1.0,  # Certified utility meter
                        extraction_confidence_score=0.98,
                    ),
                )
                records.append(record)
            except Exception as e:
                pass

        return records


class FuelInvoiceParser:
    """Parses commercial fuel invoices (Petrolimex, PVOIL, etc.) for Diesel & Petrol."""

    @classmethod
    def can_parse(cls, doc: IngestedDocument) -> bool:
        c = doc.content.lower()
        return ("xăng" in c or "dầu" in c or "petrolimex" in c or "pvoil" in c or "diesel" in c or "do 0" in c)

    @classmethod
    def parse(cls, doc: IngestedDocument) -> List[ActivityRecord]:
        records: List[ActivityRecord] = []
        content = doc.content
        lines = content.splitlines()

        supplier = "Petrolimex Vietnam"
        if "pvoil" in content.lower():
            supplier = "PVOIL Vietnam"
        elif "xăng dầu" in content.lower():
            m = re.search(r"(CÔNG\s+TY\s+(?:CỔ\s+PHẦN\s+)?XĂNG\s+DẦU[^\n\r]+)", content, re.IGNORECASE)
            if m:
                supplier = m.group(1).strip()

        date_match = re.search(r"Ngày[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})", content, re.IGNORECASE)
        date_str = date_match.group(1) if date_match else "2026-03-12"

        for idx, line in enumerate(lines):
            line_l = line.lower()
            # Skip metadata/header lines
            if any(ign in line_l for ign in ["cửa hàng", "ký hiệu", "số:", "đơn vị bán", "đơn vị mua", "thành tiền"]):
                continue

            if any(f in line_l for f in ["dầu", "diesel", "do 0", "xăng", "ron 95", "ron 92"]):
                # Split table columns by tabs, pipes, or 2+ spaces
                tokens = [t.strip() for t in re.split(r"\t|\||\s{2,}", line) if t.strip()]
                qty = None
                # Check if "Lít" is one of the tokens, the next token is typically the volume
                for t_idx, tok in enumerate(tokens):
                    if tok.lower() in ["lít", "lit"]:
                        if t_idx + 1 < len(tokens):
                            try:
                                val = clean_num(tokens[t_idx + 1])
                                if val > 0:
                                    qty = val
                                    break
                            except:
                                pass
                if not qty:
                    # Fallback regex search for volume
                    nums = re.findall(r"[\d]+(?:[\.,]\d+)?", line)
                    for num_str in nums:
                        try:
                            val = clean_num(num_str)
                            if 50.0 <= val <= 100000.0 and val != 2026:
                                qty = val
                                break
                        except:
                            continue

                if qty:
                    is_diesel = ("dầu" in line_l or "diesel" in line_l or "do" in line_l)
                    fuel_name = "Diesel Fuel (Dầu DO 0.05S)" if is_diesel else "Gasoline (Xăng RON 95)"
                    category = (
                        ActivityCategory.STATIONARY_COMBUSTION
                        if ("máy phát" in line_l or "lò hơi" in line_l or "generator" in line_l or is_diesel)
                        else ActivityCategory.MOBILE_COMBUSTION
                    )

                    record = ActivityRecord(
                        id=f"ACT-FUEL-{len(records)+1}",
                        description=f"{fuel_name} - {supplier}",
                        scope=EmissionScope.SCOPE_1,
                        category=category,
                        quantity=qty,
                        unit="liter",
                        date=date_str,
                        supplier=supplier,
                        measurement_type=MeasurementType.PRIMARY_INVOICED,
                        evidence=EvidenceProvenance(
                            source_document=doc.filename,
                            document_type="FUEL_INVOICE",
                            page_or_line=f"Line {idx+1}",
                            snippet=line.strip(),
                            extraction_method="RULE_BASED_FUEL",
                            extraction_confidence=0.96,
                        ),
                        quality=DataQualityIndicator(
                            completeness_score=0.95,
                            temporal_score=1.0,
                            geographical_score=1.0,
                            source_reliability_score=0.95,
                            extraction_confidence_score=0.96,
                        ),
                    )
                    records.append(record)
                    break

        return records


class TabularCSVParser:
    """Parses structured and semi-structured CSV manifests (Logistics, Materials, Procurement)."""

    @classmethod
    def can_parse(cls, doc: IngestedDocument) -> bool:
        return doc.file_type == "CSV" or "," in doc.content or ";" in doc.content

    @classmethod
    def parse(cls, doc: IngestedDocument) -> List[ActivityRecord]:
        records: List[ActivityRecord] = []
        reader = csv.DictReader(io.StringIO(doc.content))
        if not reader.fieldnames:
            return records

        # Normalize field names
        fields = {f.strip().lower(): f for f in reader.fieldnames if f}

        for idx, row in enumerate(reader):
            # Check for freight logistics row (weight in tons + distance in km)
            weight_col = next((fields[k] for k in fields if any(w in k for w in ["tấn", "ton", "tải trọng", "khối lượng", "weight"])), None)
            dist_col = next((fields[k] for k in fields if any(w in k for w in ["km", "quãng đường", "distance"])), None)
            tk_col = next((fields[k] for k in fields if any(w in k for w in ["ton-km", "tấn.km", "t.km"])), None)
            qty_col = next((fields[k] for k in fields if any(w in k for w in ["số lượng", "quantity", "qty", "khối lượng"])), None)
            unit_col = next((fields[k] for k in fields if any(w in k for w in ["đơn vị", "unit", "đvt"])), None)
            item_col = next((fields[k] for k in fields if any(w in k for w in ["hạng mục", "tên hàng", "mặt hàng", "item", "description", "tuyến"])), None)
            cost_col = next((fields[k] for k in fields if any(w in k for w in ["thành tiền", "tiền", "cost", "spend", "amount", "vnd"])), None)
            supplier_col = next((fields[k] for k in fields if any(w in k for w in ["nhà cung cấp", "đơn vị vận chuyển", "supplier", "vendor"])), None)
            date_col = next((fields[k] for k in fields if any(w in k for w in ["ngày", "date", "thời gian"])), None)

            date_val = row.get(date_col, "2026-03-15") if date_col else "2026-03-15"
            item_val = row.get(item_col, f"Logistics / Materials Item {idx+1}") if item_col else f"Item {idx+1}"
            supplier_val = row.get(supplier_col, "Supplier") if supplier_col else "Domestic Supplier"
            cost_val = clean_num(row[cost_col]) if cost_col and row.get(cost_col) else None

            # Case A: Logistics with weight & distance
            if weight_col and dist_col and row.get(weight_col) and row.get(dist_col):
                try:
                    w = clean_num(row[weight_col])
                    d = clean_num(row[dist_col])
                    ton_km = round(w * d, 2)
                    record = ActivityRecord(
                        id=f"ACT-LOGIS-{idx+1}",
                        description=f"Road Freight: {item_val} ({w}t x {d}km)",
                        scope=EmissionScope.SCOPE_3,
                        category=ActivityCategory.UPSTREAM_TRANSPORTATION,
                        quantity=ton_km,
                        unit="ton-km",
                        date=date_val,
                        supplier=supplier_val,
                        cost_vnd=cost_val,
                        measurement_type=MeasurementType.ESTIMATED_ACTIVITY,
                        evidence=EvidenceProvenance(
                            source_document=doc.filename,
                            document_type="FREIGHT_LOG",
                            page_or_line=f"Row {idx+2}",
                            snippet=f"{item_val} | Weight: {w} tons | Dist: {d} km | Total: {ton_km} ton-km",
                            extraction_method="CSV_TABULAR_PARSER",
                            extraction_confidence=0.95,
                        ),
                        quality=DataQualityIndicator(
                            completeness_score=0.90,
                            temporal_score=1.0,
                            geographical_score=1.0,
                            source_reliability_score=0.85,  # Route-calculated activity
                            extraction_confidence_score=0.95,
                        ),
                    )
                    records.append(record)
                    continue
                except:
                    pass

            # Case B: Physical Material items (carton, plastic, fabric in kg)
            if qty_col and unit_col and row.get(qty_col) and row.get(unit_col):
                raw_unit = str(row[unit_col]).strip().lower()
                raw_qty = row[qty_col].strip()
                if raw_qty and raw_qty.upper() != "NA" and raw_unit in ["kg", "kilogram", "tấn", "ton", "lít", "liter"]:
                    try:
                        qty_val = clean_num(raw_qty)
                        norm_unit = "kg"
                        if raw_unit in ["tấn", "ton"]:
                            qty_val = qty_val * 1000.0  # convert to kg
                        elif raw_unit in ["lít", "liter"]:
                            norm_unit = "liter"

                        record = ActivityRecord(
                            id=f"ACT-MAT-{idx+1}",
                            description=f"Purchased Materials: {item_val}",
                            scope=EmissionScope.SCOPE_3,
                            category=ActivityCategory.PURCHASED_GOODS,
                            quantity=qty_val,
                            unit=norm_unit,
                            date=date_val,
                            supplier=supplier_val,
                            cost_vnd=cost_val,
                            measurement_type=MeasurementType.PRIMARY_INVOICED,
                            evidence=EvidenceProvenance(
                                source_document=doc.filename,
                                document_type="SUPPLIER_LEDGER",
                                page_or_line=f"Row {idx+2}",
                                snippet=f"{item_val} | {qty_val} {norm_unit} | Supplier: {supplier_val}",
                                extraction_method="CSV_TABULAR_PARSER",
                                extraction_confidence=0.94,
                            ),
                            quality=DataQualityIndicator(
                                completeness_score=0.90,
                                temporal_score=1.0,
                                geographical_score=0.85,
                                source_reliability_score=0.90,
                                extraction_confidence_score=0.94,
                            ),
                        )
                        records.append(record)
                        continue
                    except:
                        pass

            # Case C: Spend-based fallback (Quantity is NA / missing, but Cost is available!)
            if cost_val and cost_val > 0:
                is_freight = any(w in item_val.lower() for w in ["vận chuyển", "logistics", "freight", "bốc xếp", "xe"])
                category = ActivityCategory.UPSTREAM_TRANSPORTATION if is_freight else ActivityCategory.PURCHASED_GOODS

                record = ActivityRecord(
                    id=f"ACT-SPEND-{idx+1}",
                    description=f"Spend-based Estimate: {item_val}",
                    scope=EmissionScope.SCOPE_3,
                    category=category,
                    quantity=cost_val,
                    unit="VND",
                    date=date_val,
                    supplier=supplier_val,
                    cost_vnd=cost_val,
                    measurement_type=MeasurementType.SPEND_BASED_PROXY,
                    evidence=EvidenceProvenance(
                        source_document=doc.filename,
                        document_type="SPEND_LEDGER",
                        page_or_line=f"Row {idx+2}",
                        snippet=f"Missing physical quantity. Expense: {cost_val:,.0f} VND ({item_val})",
                        extraction_method="CSV_FALLBACK_SPEND",
                        extraction_confidence=0.90,
                    ),
                    quality=DataQualityIndicator(
                        completeness_score=0.55,  # Missing physical volume
                        temporal_score=0.90,
                        geographical_score=0.80,
                        source_reliability_score=0.40,  # Spend-based proxy has low reliability tier
                        extraction_confidence_score=0.90,
                    ),
                )
                records.append(record)

        return records
