"""MarkItDown-powered document normalization with OCR and evidence tracking."""

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

# Check OCR availability
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
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
    """Converts multi-format business documents into structured Markdown for EcoStream."""

    def __init__(self, enable_ocr: bool = True, tesseract_lang: str = "vie+eng"):
        self.enable_ocr = enable_ocr
        self.tesseract_lang = tesseract_lang
        self.md_engine = None
        if _MARKITDOWN_AVAILABLE:
            try:
                self.md_engine = MarkItDown()
            except Exception as e:
                self.md_engine = None

    def normalize_file(self, filepath: str) -> NormalizedDocumentContent:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1].lower()

        # 1. Plain text and CSV Fast-Path
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

        # 2. MarkItDown for Digital PDF, Excel (.xlsx, .xls), Word (.docx)
        if self.md_engine and ext in [".pdf", ".xlsx", ".xls", ".docx", ".pptx", ".html"]:
            try:
                result = self.md_engine.convert(filepath)
                text = (result.text_content or "").strip()

                # If PDF produced near-empty text, it is likely a scanned PDF -> attempt OCR
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
            except Exception as e:
                # Fall through to OCR or fallback reader
                pass

        # 3. Direct Image OCR (PNG, JPG, JPEG, TIFF)
        if ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"] and self.enable_ocr and _OCR_LIBS_AVAILABLE:
            try:
                img = Image.open(filepath)
                ocr_text = pytesseract.image_to_string(img, lang=self.tesseract_lang).strip()
                if ocr_text:
                    return NormalizedDocumentContent(
                        markdown_content=ocr_text,
                        converter_used="LOCAL_TESSERACT_IMAGE_OCR",
                        ocr_applied=True,
                        page_count=1,
                        raw_metadata={"source_path": filepath, "original_filename": filename},
                    )
            except Exception as e:
                # Check for Gemini Vision fallback if API key available
                vision_text = self._try_gemini_vision(filepath)
                if vision_text:
                    return NormalizedDocumentContent(
                        markdown_content=vision_text,
                        converter_used="GEMINI_VISION_OCR",
                        ocr_applied=True,
                        page_count=1,
                        raw_metadata={"source_path": filepath, "original_filename": filename},
                    )

        # 4. Scanned PDF fallback
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

        # 5. Multi-tier Graceful Fallback
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

    def _try_gemini_vision(self, filepath: str) -> Optional[str]:
        """Vision LLM fallback if local OCR is unavailable and GEMINI_API_KEY is configured."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            import urllib.request
            import base64
            import json

            with open(filepath, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            ext = os.path.splitext(filepath)[1].lower().replace(".", "")
            mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Transcribe this business invoice or receipt into clean Markdown. Preserve all numbers, quantities, units, and headers exactly."},
                        {"inline_data": {"mime_type": mime, "data": b64_data}}
                    ]
                }]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None
