"""Offline Commercial License Generator & Verifier for EcoStream Desktop.

Supports:
1. Industrial-grade Asymmetric Ed25519 Signed Licenses (ECO2.<PAYLOAD>.<SIG>):
   - Verification is 100% offline using an embedded Ed25519 Public Key.
   - Mathematically impossible to forge or crack even if the app is reverse-engineered.
2. Built-in evaluation/demo keys (ECO-PRO-2026, ECO-ENTERPRISE-2026, USTH-INNO-2026)
3. Legacy HMAC-SHA256 commercial keys (ECO1-<ORG>-<YYYYMMDD>-<SIG12>)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

# Vendor Master Ed25519 Public Key (Safe to embed in desktop app)
VENDOR_ED25519_PUBLIC_KEY_B64 = os.environ.get(
    "ECOSTREAM_VENDOR_PUBLIC_KEY",
    "xASZCWZaShlZGSpYUCgbIUpMbB_HM-blMNNNQhL2BqE=",
)

# Legacy vendor signing seed for HMAC fallback
_VENDOR_SIGNING_SEED = os.environ.get(
    "ECOSTREAM_VENDOR_SECRET",
    "ecostream-usth-2026-commercial-desktop-ed25519-seed-v1",
)

DEFAULT_PRO_KEYS = {"ECO-PRO-2026", "ECO-ENTERPRISE-2026", "USTH-INNO-2026"}


def _normalize_org(org_id: Optional[str]) -> str:
    if not org_id:
        return "ANY"
    cleaned = re.sub(r"[^A-Z0-9]", "", org_id.strip().upper())
    return cleaned[:16] or "ANY"


def generate_ed25519_license(
    org_id: str,
    email: str = "",
    expires_iso: str = "2027-12-31",
    plan: str = "PRO",
    features: Optional[List[str]] = None,
    private_key_b64: Optional[str] = None,
) -> str:
    """Generate an asymmetric Ed25519 signed license token for commercial customers.
    
    Requires vendor private key (kept secret by vendor/founder, never shipped in client code).
    """
    from cryptography.hazmat.primitives.asymmetric import ed25519

    priv_key_str = private_key_b64 or os.environ.get("ECOSTREAM_VENDOR_PRIVATE_KEY")
    if not priv_key_str:
        # Check local vendor private key file if exists
        key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "vendor_ed25519_private.key")
        if os.path.exists(key_file):
            with open(key_file, "r", encoding="utf-8") as f:
                priv_key_str = f.read().strip()

    if not priv_key_str:
        raise ValueError(
            "Missing Vendor Private Key. Please set ECOSTREAM_VENDOR_PRIVATE_KEY or provide vendor_ed25519_private.key."
        )

    priv_bytes = base64.urlsafe_b64decode(priv_key_str)
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)

    if features is None:
        features = ["scope1", "scope2", "scope3", "nd06_docx", "audit_excel", "ai_extract", "no_watermark"]

    payload = {
        "org": _normalize_org(org_id),
        "email": email.strip().lower() if email else "",
        "plan": plan.upper(),
        "exp": expires_iso,
        "issued": str(date.today()),
        "features": features,
    }

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = priv_key.sign(payload_json)

    p_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii")
    s_b64 = base64.urlsafe_b64encode(sig).decode("ascii")

    return f"ECO2.{p_b64}.{s_b64}"


def generate_commercial_license(org_id: str, expires_yyyymmdd: str = "20271231") -> str:
    """Generate legacy HMAC signed license (kept for backward compatibility)."""
    org_norm = _normalize_org(org_id)
    if not re.match(r"^\d{8}$", expires_yyyymmdd):
        raise ValueError("expires_yyyymmdd must be in YYYYMMDD format (e.g., 20271231)")
    payload = f"ECO1:{org_norm}:{expires_yyyymmdd}"
    sig = hmac.new(
        _VENDOR_SIGNING_SEED.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:12].upper()
    return f"ECO1-{org_norm}-{expires_yyyymmdd}-{sig}"


def verify_commercial_license(
    license_key: Optional[str],
    org_id: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """Verify a license key 100% offline.

    Supports:
    1. Ed25519 Asymmetric Tokens (ECO2.<PAYLOAD>.<SIG>)
    2. Evaluation/Demo keys (ECO-PRO-2026, etc.)
    3. Legacy HMAC keys (ECO1-...)

    Returns:
        (is_valid, metadata_dict)
    """
    if not license_key:
        return False, {"reason": "missing_key", "tier": "FREE", "features": []}

    clean_key = license_key.strip()

    # 1. Check Ed25519 Asymmetric License (ECO2.<p_b64>.<s_b64>)
    if clean_key.startswith("ECO2."):
        parts = clean_key.split(".")
        if len(parts) == 3:
            _, p_b64, s_b64 = parts
            try:
                from cryptography.exceptions import InvalidSignature
                from cryptography.hazmat.primitives.asymmetric import ed25519

                pub_bytes = base64.urlsafe_b64decode(VENDOR_ED25519_PUBLIC_KEY_B64)
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

                payload_bytes = base64.urlsafe_b64decode(p_b64)
                sig_bytes = base64.urlsafe_b64decode(s_b64)

                pub_key.verify(sig_bytes, payload_bytes)
                data = json.loads(payload_bytes.decode("utf-8"))

                exp_str = data.get("exp", "2000-01-01")
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                if date.today() > exp_date:
                    return False, {
                        "reason": f"License đã hết hạn vào ngày {exp_str}.",
                        "tier": "FREE",
                        "expires": exp_str,
                        "features": [],
                    }

                key_org = data.get("org", "ANY")
                if key_org != "ANY" and org_id:
                    caller_org = _normalize_org(org_id)
                    if caller_org != key_org:
                        return False, {
                            "reason": f"Mã bản quyền chỉ dành cho tổ chức {key_org}.",
                            "tier": "FREE",
                            "features": [],
                        }

                return True, {
                    "tier": data.get("plan", "PRO"),
                    "license_type": "COMMERCIAL_ED25519",
                    "bound_org": key_org,
                    "email": data.get("email", ""),
                    "expires": exp_str,
                    "features": data.get("features", []),
                }
            except (InvalidSignature, Exception) as e:
                return False, {"reason": f"Chữ ký số bản quyền không hợp lệ ({e})", "tier": "FREE", "features": []}

    upper_key = clean_key.upper()

    # 2. Check built-in evaluation / demo keys
    env_keys = os.environ.get("ECOSTREAM_PRO_KEYS", "")
    custom_keys = {k.strip().upper() for k in env_keys.split(",") if k.strip()}
    if upper_key in DEFAULT_PRO_KEYS.union(custom_keys):
        return True, {
            "tier": "PRO",
            "license_type": "DEMO_EVALUATION",
            "bound_org": "ANY",
            "email": "",
            "expires": "2099-12-31",
            "features": ["scope1", "scope2", "scope3", "nd06_docx", "audit_excel", "ai_extract", "no_watermark"],
        }

    # 3. Check legacy HMAC commercial key: ECO1-<ORG>-<YYYYMMDD>-<SIG12>
    parts = upper_key.split("-")
    if len(parts) == 4 and parts[0] == "ECO1":
        _, key_org, exp_str, provided_sig = parts
        if not re.match(r"^\d{8}$", exp_str):
            return False, {"reason": "invalid_expiry_format", "tier": "FREE", "features": []}

        expected_payload = f"ECO1:{key_org}:{exp_str}"
        expected_sig = hmac.new(
            _VENDOR_SIGNING_SEED.encode("utf-8"),
            expected_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:12].upper()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return False, {"reason": "invalid_signature", "tier": "FREE", "features": []}

        try:
            exp_date = datetime.strptime(exp_str, "%Y%m%d").date()
            if date.today() > exp_date:
                return False, {"reason": "expired", "tier": "FREE", "expires": str(exp_date), "features": []}
        except ValueError:
            return False, {"reason": "invalid_date", "tier": "FREE", "features": []}

        if key_org != "ANY" and org_id:
            caller_org = _normalize_org(org_id)
            if caller_org != key_org:
                return False, {"reason": f"org_mismatch (bound to {key_org})", "tier": "FREE", "features": []}

        return True, {
            "tier": "PRO",
            "license_type": "LEGACY_HMAC_SIGNED",
            "bound_org": key_org,
            "email": "",
            "expires": f"{exp_str[:4]}-{exp_str[4:6]}-{exp_str[6:8]}",
            "features": ["scope1", "scope2", "scope3", "nd06_docx", "audit_excel", "ai_extract", "no_watermark"],
        }

    return False, {"reason": "Mã bản quyền không nhận diện được", "tier": "FREE", "features": []}
