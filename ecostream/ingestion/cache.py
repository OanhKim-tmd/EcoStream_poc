"""SHA-256 caching layer for MarkItDown document conversion."""

import os
import hashlib
from typing import Optional


class IngestionCache:
    """Manages persistent caching of parsed markdown conversions by file content hash."""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            claude_cache = os.path.join(base_dir, ".claude", "references", "cache")
            ref_cache = os.path.join(base_dir, "references", "cache")
            cache_dir = claude_cache if os.path.exists(os.path.dirname(claude_cache)) else ref_cache
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    @staticmethod
    def compute_sha256(file_path_or_bytes: str | bytes) -> str:
        """Compute SHA-256 hash of a file path or raw bytes."""
        hasher = hashlib.sha256()
        if isinstance(file_path_or_bytes, bytes):
            hasher.update(file_path_or_bytes)
        elif isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        return hasher.hexdigest()

    def get(self, sha256_hash: str) -> Optional[str]:
        """Retrieve cached markdown string if present."""
        target_file = os.path.join(self.cache_dir, f"{sha256_hash}.md")
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def store(self, sha256_hash: str, markdown_content: str) -> str:
        """Store converted markdown in cache directory."""
        target_file = os.path.join(self.cache_dir, f"{sha256_hash}.md")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return target_file


# Global singleton
_global_cache: Optional[IngestionCache] = None


def get_ingestion_cache() -> IngestionCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = IngestionCache()
    return _global_cache
