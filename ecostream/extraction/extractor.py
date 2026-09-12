"""ExtractionEngine orchestrating multi-format document extraction with provenance tracking."""

import os
import json
from typing import List
from ecostream.ingestion.loaders import IngestedDocument
from ecostream.models.activity import ActivityRecord
from ecostream.extraction.parsers import EVNBillParser, FuelInvoiceParser, TabularCSVParser


class ExtractionEngine:
    """Orchestrates parsing of incoming SME business documents into validated ActivityRecords."""

    def __init__(self, enable_live_llm: bool = False):
        self.enable_live_llm = enable_live_llm
        self.gemini_key = os.environ.get("GEMINI_API_KEY")

    def extract_document(self, doc: IngestedDocument) -> List[ActivityRecord]:
        records: List[ActivityRecord] = []

        # 1. Check EVN Electricity Bill
        if EVNBillParser.can_parse(doc):
            parsed = EVNBillParser.parse(doc)
            if parsed:
                records.extend(parsed)

        # 2. Check Fuel Invoice
        if FuelInvoiceParser.can_parse(doc):
            parsed = FuelInvoiceParser.parse(doc)
            if parsed:
                records.extend(parsed)

        # 3. Check Tabular / CSV manifests
        if TabularCSVParser.can_parse(doc):
            parsed = TabularCSVParser.parse(doc)
            if parsed:
                records.extend(parsed)

        # 4. Optional Live LLM Fallback (if enabled and no records found)
        if not records and self.enable_live_llm and self.gemini_key:
            llm_records = self._extract_with_gemini(doc)
            if llm_records:
                records.extend(llm_records)

        return records

    def extract_batch(self, documents: List[IngestedDocument]) -> List[ActivityRecord]:
        all_records: List[ActivityRecord] = []
        for doc in documents:
            recs = self.extract_document(doc)
            all_records.extend(recs)
        return all_records

    def _extract_with_gemini(self, doc: IngestedDocument) -> List[ActivityRecord]:
        """Optional connector to Google Gemini API for arbitrary unstructured invoice extraction."""
        # Gracefully handled if httpx / requests are present
        try:
            import httpx
            # If user has a real key, we can call Gemini Flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
            prompt = (
                "You are an expert GHG carbon accounting assistant. Extract energy, fuel, and material activity data from this document. "
                "Return a JSON array of objects with fields: description, scope (Scope 1, Scope 2, Scope 3), "
                "category, quantity (float), unit, date, supplier, snippet.\n\n"
                f"Document content:\n{doc.content[:4000]}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
            resp = httpx.post(url, json=payload, timeout=20.0)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                items = json.loads(text)
                # Map to ActivityRecord
                results = []
                for i, it in enumerate(items):
                    # Basic mapping
                    from ecostream.models.activity import (
                        EmissionScope,
                        ActivityCategory,
                        MeasurementType,
                        EvidenceProvenance,
                        DataQualityIndicator,
                    )
                    results.append(
                        ActivityRecord(
                            id=f"ACT-LLM-{i+1}",
                            description=it.get("description", "LLM Extracted Activity"),
                            scope=EmissionScope(it.get("scope", "Scope 1")),
                            category=ActivityCategory.STATIONARY_COMBUSTION,
                            quantity=float(it.get("quantity", 0)),
                            unit=it.get("unit", "kg"),
                            date=it.get("date"),
                            supplier=it.get("supplier"),
                            measurement_type=MeasurementType.PRIMARY_INVOICED,
                            evidence=EvidenceProvenance(
                                source_document=doc.filename,
                                document_type="LLM_EXTRACTED",
                                snippet=it.get("snippet", doc.content[:100]),
                                extraction_method="GEMINI_LLM",
                                extraction_confidence=0.92,
                            ),
                            quality=DataQualityIndicator(
                                completeness_score=0.90,
                                temporal_score=0.90,
                                geographical_score=0.85,
                                source_reliability_score=0.90,
                                extraction_confidence_score=0.92,
                            ),
                        )
                    )
                return results
        except Exception as e:
            print(f"Notice: Gemini fallback skipped ({e})")
        return []
