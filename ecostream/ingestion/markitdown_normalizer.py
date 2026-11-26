"""MarkItDown-powered document normalization with evidence tracking.

No OCR: only documents with a text layer are read (digital PDF, Excel, Word,
CSV). Vietnamese e-invoices are issued as XML-backed digital PDFs. Scanned PDFs
and images are not supported; their data is entered manually in the survey.
"""

import os
from pydantic import BaseModel, Field

# Suppress noisy device discovery logs
os.environ.setdefault("ORT_LOG_LEVEL", "3")

# Check MarkItDown availability
try:
    from markitdown import MarkItDown
    _MARKITDOWN_AVAILABLE = True
except Exception:
    _MARKITDOWN_AVAILABLE = False


class NormalizedDocumentContent(BaseModel):
    """Encapsulates converted Markdown text with audit metadata."""
    markdown_content: str
    converter_used: str
    ocr_applied: bool = False
    page_count: int = 1
    raw_metadata: dict = Field(default_factory=dict)


class MarkItDownNormalizer:
    """Converts multi-format business documents into structured Markdown for EcoStream.

    Supported formats:
     - .txt / .csv / .json / .log  → direct text read
     - .xlsx / .xls / .docx / .pptx / .html → Microsoft MarkItDown
     - .pdf (text layer) → Microsoft MarkItDown

    Scanned PDFs and image files are intentionally NOT processed (no OCR).
    `ocr_applied` is kept on the result model for compatibility and is always False.
    """

    def __init__(self, **_ignored):
        self.md_engine = None
        if _MARKITDOWN_AVAILABLE:
            try:
                self.md_engine = MarkItDown()
            except Exception:
                self.md_engine = None

    def normalize_file(self, filepath: str) -> NormalizedDocumentContent:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1].lower()

        # 1. Plain text / CSV / JSON fast-path
        if ext in [".txt", ".log", ".ocr", ".csv", ".json"]:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return NormalizedDocumentContent(
                markdown_content=content,
                converter_used="NATIVE_TEXT",
                ocr_applied=False,
                page_count=1,
                raw_metadata={"source_path": filepath, "original_filename": filename},
            )

        # 2. MarkItDown for digital PDF, Excel, Word, PowerPoint, HTML
        if self.md_engine and ext in [".pdf", ".xlsx", ".xls", ".docx", ".pptx", ".html"]:
            try:
                result = self.md_engine.convert(filepath)
                text = (result.text_content or "").strip()
                if text:
                    converter_tag = f"MARKITDOWN_{ext.replace('.', '').upper()}"
                    return NormalizedDocumentContent(
                        markdown_content=text,
                        converter_used=converter_tag,
                        ocr_applied=False,
                        page_count=1,
                        raw_metadata={
                            "source_path": filepath,
                            "original_filename": filename,
                            "title": getattr(result, "title", None),
                        },
                    )
            except Exception:
                pass

        # 3. Last-resort text read
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return NormalizedDocumentContent(
                markdown_content=content,
                converter_used="FALLBACK_TEXT_READER",
                ocr_applied=False,
                page_count=1,
                raw_metadata={
                    "source_path": filepath,
                    "original_filename": filename,
                    "warning": f"Unsupported or unparsed binary format {ext}",
                },
            )
        except Exception:
            return NormalizedDocumentContent(
                markdown_content="",
                converter_used="EMPTY_FALLBACK",
                ocr_applied=False,
                page_count=1,
                raw_metadata={"source_path": filepath, "original_filename": filename},
            )

