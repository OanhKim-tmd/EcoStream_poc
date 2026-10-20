"""Data Encryption at Rest Engine for EcoStream.

Provides AES-256 authenticated encryption (Fernet / AES-CBC-HMAC) for customer raw business
documents (PDF invoices, XML e-invoices, Excel sheets) stored in the workspace.
"""

import os
import base64
import hashlib
from typing import Optional, Tuple
from cryptography.fernet import Fernet


class StorageEncryption:
    """Handles encryption and decryption of sensitive files at rest."""

    _master_key: Optional[bytes] = None

    @classmethod
    def get_or_create_key(cls, run_id: Optional[str] = None) -> bytes:
        """Retrieve an encryption key from environment or derive a per-run key."""
        # 1. User-configured master encryption key
        env_key = os.environ.get("ECOSTREAM_ENCRYPTION_KEY")
        if env_key:
            # Ensure valid 32-byte urlsafe base64 key
            key_bytes = env_key.encode("utf-8")
            if len(key_bytes) == 44:
                return key_bytes
            # Derive 32-byte key via SHA-256
            derived = hashlib.sha256(key_bytes).digest()
            return base64.urlsafe_b64encode(derived)

        # 2. Per-run isolated key derived from run_id and machine secret
        salt = run_id or "ecostream_default_salt"
        machine_seed = os.environ.get("HOSTNAME", "local_ecostream_node").encode("utf-8")
        derived = hashlib.sha256(salt.encode("utf-8") + machine_seed).digest()
        return base64.urlsafe_b64encode(derived)

    @classmethod
    def encrypt_file(cls, src_path: str, dest_path: str, key: Optional[bytes] = None) -> str:
        """Encrypt a file at rest using AES-256 Fernet."""
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file not found: {src_path}")

        fernet_key = key or cls.get_or_create_key()
        fernet = Fernet(fernet_key)

        with open(src_path, "rb") as f:
            plaintext = f.read()

        ciphertext = fernet.encrypt(plaintext)
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(ciphertext)

        return dest_path

    @classmethod
    def decrypt_file_to_memory(cls, enc_path: str, key: Optional[bytes] = None) -> bytes:
        """Decrypt an encrypted file into memory without writing plaintext to disk."""
        if not os.path.exists(enc_path):
            raise FileNotFoundError(f"Encrypted file not found: {enc_path}")

        fernet_key = key or cls.get_or_create_key()
        fernet = Fernet(fernet_key)

        with open(enc_path, "rb") as f:
            ciphertext = f.read()

        return fernet.decrypt(ciphertext)
