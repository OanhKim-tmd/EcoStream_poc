"""EcoStream - facility-level GHG inventory survey tool (Decree 06/2022/ND-CP), runs fully offline."""

__version__ = "0.3.0"

import os

# Suppress verbose ONNX device warning logs if ONNX is used by markitdown/magika
os.environ.setdefault("ORT_LOG_LEVEL", "3")
