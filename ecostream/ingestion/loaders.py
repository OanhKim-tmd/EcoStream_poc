"""Multi-format document loader for SME invoices, spreadsheets, and receipt transcripts."""

import csv
import io
import os
from typing import List, Optional
from pydantic import BaseModel, Field


from ecostream.ingestion.markitdown_normalizer import MarkItDownNormalizer


class IngestedDocument(BaseModel):
    """Normalized ingested document representation."""
    filename: str
    file_type: str = Field(description="TXT, CSV, PDF_TEXT, PDF_OCR, EXCEL_SHEET, DOCX, IMAGE_OCR, JSON")
    content: str = Field(description="Raw text content or serialized Markdown table")
    metadata: dict = Field(default_factory=dict)


class DocumentIngestionLoader:
    """Loads and normalizes business documents from filesystem or web uploads."""

    _normalizer = MarkItDownNormalizer()

    @classmethod
    def load_from_text(cls, filename: str, text: str, metadata: Optional[dict] = None) -> IngestedDocument:
        ftype = "TXT"
        if filename.endswith(".csv"):
            ftype = "CSV"
        elif filename.endswith(".pdf"):
            ftype = "PDF_TEXT"
        elif filename.endswith(".json"):
            ftype = "JSON"
        return IngestedDocument(
            filename=filename,
            file_type=ftype,
            content=text,
            metadata=metadata or {},
        )

    @classmethod
    def load_file(cls, filepath: str) -> IngestedDocument:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1].lower()

        # Fast path for plain text and logs
        if ext in [".txt", ".ocr", ".log"]:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return cls.load_from_text(
                    filename,
                    f.read(),
                    {"source_path": filepath, "original_filename": filename, "converter": "NATIVE_TEXT"},
                )

        # Multi-format normalization via MarkItDown & OCR Normalizer
        normalized = cls._normalizer.normalize_file(filepath)

        ftype_map = {
            ".csv": "CSV",
            ".pdf": "PDF_OCR" if normalized.ocr_applied else "PDF_TEXT",
            ".xlsx": "EXCEL_SHEET",
            ".xls": "EXCEL_SHEET",
            ".docx": "DOCX",
            ".png": "IMAGE_OCR",
            ".jpg": "IMAGE_OCR",
            ".jpeg": "IMAGE_OCR",
            ".json": "JSON",
        }
        file_type = ftype_map.get(ext, "TXT")

        meta = {
            "source_path": filepath,
            "original_filename": filename,
            "converter": normalized.converter_used,
            "ocr_applied": normalized.ocr_applied,
            "page_count": normalized.page_count,
        }
        meta.update(normalized.raw_metadata)

        return IngestedDocument(
            filename=filename,
            file_type=file_type,
            content=normalized.markdown_content,
            metadata=meta,
        )

    @classmethod
    def load_directory(cls, dir_path: str) -> List[IngestedDocument]:
        documents = []
        if not os.path.isdir(dir_path):
            return documents

        for fname in sorted(os.listdir(dir_path)):
            fpath = os.path.join(dir_path, fname)
            if os.path.isfile(fpath):
                try:
                    doc = cls.load_file(fpath)
                    documents.append(doc)
                except Exception as e:
                    print(f"Warning: Failed to load {fpath}: {e}")
        return documents


# Alias for concise import
DocumentLoader = DocumentIngestionLoader
