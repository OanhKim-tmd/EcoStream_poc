"""SHA-256 caching layer for MarkItDown document conversion."""
from __future__ import annotations

import os
import sys
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from ecostream.privacy.encryption import StorageEncryption


class IngestionCache:
    """Manages persistent caching of parsed markdown conversions by file content hash."""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            if getattr(sys, "frozen", False):
                if sys.platform == "darwin":
                    user_root = os.path.expanduser("~/Library/Application Support/EcoStream")
                elif sys.platform == "win32":
                    user_root = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "EcoStream")
                else:
                    user_root = os.path.expanduser("~/.ecostream")
                cache_dir = os.path.join(user_root, "cache")
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                # Cache is generated runtime data, never project reference material.
                cache_dir = os.path.join(base_dir, ".cache", "ecostream", "ingestion")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        # Deployment cache is encrypted with the stable deployment key. On local runs
        # without a configured key, cache only in memory (no derived/plaintext disk key).
        configured_key = os.environ.get("ECOSTREAM_ENCRYPTION_KEY")
        self._memory_cache: dict[str, str] = {}
        self._fernet = None
        if configured_key:
            self._fernet = Fernet(StorageEncryption.get_or_create_key("ingestion-cache"))
        # Remove legacy plaintext cache entries created by previous releases.
        # Cache is reproducible from source documents and may be safely discarded.
        for name in os.listdir(self.cache_dir):
            if name.endswith(".md") and len(name) == 67:
                candidate = name[:-3]
                if len(candidate) == 64 and all(ch in "0123456789abcdef" for ch in candidate.lower()):
                    try:
                        os.remove(os.path.join(self.cache_dir, name))
                    except OSError:
                        pass

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

    def _cache_path(self, sha256_hash: str) -> str:
        if len(sha256_hash) != 64 or any(ch not in "0123456789abcdef" for ch in sha256_hash.lower()):
            raise ValueError("Invalid SHA-256 cache key")
        return os.path.join(self.cache_dir, f"{sha256_hash}.enc")

    def get(self, sha256_hash: str) -> Optional[str]:
        """Retrieve and decrypt cached markdown; unreadable entries become cache misses."""
        if self._fernet is None:
            return self._memory_cache.get(sha256_hash)
        target_file = self._cache_path(sha256_hash)
        if not os.path.isfile(target_file):
            return None
        try:
            with open(target_file, "rb") as f:
                plaintext = self._fernet.decrypt(f.read())
            return plaintext.decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, OSError):
            # Includes stale local ephemeral-key entries after process restart.
            return None

    def store(self, sha256_hash: str, markdown_content: str) -> str:
        """Encrypt converted markdown before storing it in the cache."""
        if self._fernet is None:
            self._memory_cache[sha256_hash] = markdown_content
            return "<memory>"
        target_file = self._cache_path(sha256_hash)
        ciphertext = self._fernet.encrypt(markdown_content.encode("utf-8"))
        temp_file = f"{target_file}.tmp"
        with open(temp_file, "wb") as f:
            f.write(ciphertext)
        os.replace(temp_file, target_file)
        return target_file


# Global singleton
_global_cache: Optional[IngestionCache] = None


def get_ingestion_cache() -> IngestionCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = IngestionCache()
    return _global_cache
