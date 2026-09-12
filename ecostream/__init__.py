"""EcoStream - AI-powered Carbon Footprint & Data Reliability Engine.

Tailored for Vietnamese SMEs facing supply chain and export compliance (CBAM, Decree 06/2022/ND-CP).
"""

__version__ = "0.1.0"

import sys
import os

# Auto-discover extended packages (MarkItDown, OCR, etc.)
for _candidate in [
    os.path.join(os.environ.get("SNAP_USER_COMMON", ""), "lib/python3.13/site-packages"),
    "/home/oanh/snap/antigravity-cli/common/lib/python3.13/site-packages",
]:
    if _candidate and os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)

# Suppress verbose ONNX device warning logs if ONNX is used by markitdown/magika
os.environ.setdefault("ORT_LOG_LEVEL", "3")
