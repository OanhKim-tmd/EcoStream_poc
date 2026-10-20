"""MarkItDown-powered document normalization with OCR and evidence tracking.

OCR scope: PDF documents only (digital text extraction via MarkItDown, with
pytesseract fallback for scanned/image-embedded PDFs). Image files (PNG, JPG)
are not processed — Vietnamese e-invoices are issued as XML-backed digital PDFs
and do not require image OCR.
"""

import os
import sys
from typing import Optional, Tuple
from pydantic import BaseModel, Field

# Ensure extra site packages (snap / common) are loaded
for _candidate in [
    os.path.join(os.environ.get("SNAP_USER_COMMON", ""), "lib/python3.13/site-packages"),
    "/home/oanh/snap/antigravity-cli/common/lib/python3.13/site-packages",
]:
    if _candidate and os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)

# Suppress noisy device discovery logs
os.environ.setdefault("ORT_LOG_LEVEL", "3")

# Check MarkItDown availability
try:
    from markitdown import MarkItDown
    _MARKITDOWN_AVAILABLE = True
except Exception:
    _MARKITDOWN_AVAILABLE = False

# Check OCR availability (PDF-only path via pytesseract + pdf2image)
try:
    import pytesseract
    from pdf2image import convert_from_path
    _OCR_LIBS_AVAILABLE = True
except Exception:
    _OCR_LIBS_AVAILABLE = False


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
     - .pdf (digital)  → Microsoft MarkItDown
     - .pdf (scanned)  → pytesseract OCR fallback (vie+eng)

    Image files (.png, .jpg, etc.) are intentionally NOT processed:
    Vietnamese e-invoices arrive as XML-backed digital PDFs, not image scans.
    """

    def __init__(self, enable_ocr: bool = True, tesseract_lang: str = "vie+eng"):
        self.enable_ocr = enable_ocr
        self.tesseract_lang = tesseract_lang
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

                # If PDF returned near-empty text it is likely a scanned PDF → OCR
                if ext == ".pdf" and len(text) < 50 and self.enable_ocr and _OCR_LIBS_AVAILABLE:
                    ocr_text, pages = self._perform_pdf_ocr(filepath)
                    if ocr_text:
                        return NormalizedDocumentContent(
                            markdown_content=ocr_text,
                            converter_used="MARKITDOWN_PDF_OCR",
                            ocr_applied=True,
                            page_count=pages,
                            raw_metadata={"source_path": filepath, "original_filename": filename},
                        )

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

        # 3. Scanned PDF fallback (when MarkItDown is unavailable or produced nothing)
        if ext == ".pdf" and self.enable_ocr and _OCR_LIBS_AVAILABLE:
            ocr_text, pages = self._perform_pdf_ocr(filepath)
            if ocr_text:
                return NormalizedDocumentContent(
                    markdown_content=ocr_text,
                    converter_used="LOCAL_TESSERACT_PDF_OCR",
                    ocr_applied=True,
                    page_count=pages,
                    raw_metadata={"source_path": filepath, "original_filename": filename},
                )

        # 4. Last-resort text read
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

    def _perform_pdf_ocr(self, filepath: str) -> Tuple[str, int]:
        """Rasterize PDF pages and perform OCR preserving page delimiters."""
        if not _OCR_LIBS_AVAILABLE:
            return "", 0
        try:
            from PIL import Image
            images = convert_from_path(filepath, dpi=200)
            annotated_pages = []
            for idx, img in enumerate(images, 1):
                try:
                    text = pytesseract.image_to_string(img, lang=self.tesseract_lang).strip()
                except Exception:
                    text = ""
                if text:
                    annotated_pages.append(f"<!-- page: {idx} -->\n{text}")
            return "\n\n".join(annotated_pages), len(images)
        except Exception:
            return "", 0

