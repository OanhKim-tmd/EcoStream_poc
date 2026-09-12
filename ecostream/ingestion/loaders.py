"""Multi-format document loader for SME invoices, spreadsheets, and receipt transcripts."""

import csv
import io
import os
from typing import List, Optional
from pydantic import BaseModel, Field


class IngestedDocument(BaseModel):
    """Normalized ingested document representation."""
    filename: str
    file_type: str = Field(description="TXT, CSV, PDF_TEXT, EXCEL, JSON")
    content: str = Field(description="Raw text content or serialized table")
    metadata: dict = Field(default_factory=dict)


class DocumentIngestionLoader:
    """Loads and normalizes business documents from filesystem or web uploads."""

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

        if ext in [".txt", ".ocr", ".log"]:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return cls.load_from_text(filename, f.read(), {"source_path": filepath})

        elif ext == ".csv":
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return IngestedDocument(
                filename=filename,
                file_type="CSV",
                content=content,
                metadata={"source_path": filepath},
            )

        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return IngestedDocument(
                    filename=filename,
                    file_type="JSON",
                    content=f.read(),
                    metadata={"source_path": filepath},
                )

        else:
            # Fallback text reading
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return IngestedDocument(
                    filename=filename,
                    file_type="TXT",
                    content=f.read(),
                    metadata={"source_path": filepath},
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
