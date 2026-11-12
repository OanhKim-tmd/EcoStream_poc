"""Offline Commercial License Generator & Verifier for EcoStream Desktop.

Supports:
1. Built-in evaluation/demo keys (ECO-PRO-2026, ECO-ENTERPRISE-2026, USTH-INNO-2026)
2. Offline signed commercial keys bound to Organization ID / Tax Code & Expiration Date:
   Format: ECO1-<ORG_SLUG>-<YYYYMMDD>-<SIGNATURE12>
   Verified 100% offline using Ed25519 / HMAC-SHA256 without requiring internet access.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

# Vendor master signing seed (in production, override via ECOSTREAM_VENDOR_SECRET at build time)
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


def generate_commercial_license(org_id: str, expires_yyyymmdd: str = "20271231") -> str:
    """Generate a signed offline commercial license key for an SME customer."""
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
) -> Tuple[bool, Dict[str, str]]:
    """Verify a license key 100% offline.

    Returns (is_valid_pro, metadata_dict).
    """
    if not license_key:
        return False, {"reason": "missing_key", "tier": "FREE"}

    clean_key = license_key.strip().upper()

    # 1. Check built-in / environment demo keys
    env_keys = os.environ.get("ECOSTREAM_PRO_KEYS", "")
    custom_keys = {k.strip().upper() for k in env_keys.split(",") if k.strip()}
    if clean_key in DEFAULT_PRO_KEYS.union(custom_keys):
        return True, {
            "tier": "PRO",
            "license_type": "DEMO_ENTERPRISE",
            "bound_org": "ANY",
            "expires": "2099-12-31",
        }

    # 2. Check structured commercial key: ECO1-<ORG>-<YYYYMMDD>-<SIG12>
    parts = clean_key.split("-")
    if len(parts) == 4 and parts[0] == "ECO1":
        _, key_org, exp_str, provided_sig = parts
        if not re.match(r"^\d{8}$", exp_str):
            return False, {"reason": "invalid_expiry_format", "tier": "FREE"}

        expected_payload = f"ECO1:{key_org}:{exp_str}"
        expected_sig = hmac.new(
            _VENDOR_SIGNING_SEED.encode("utf-8"),
            expected_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:12].upper()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return False, {"reason": "invalid_signature", "tier": "FREE"}

        # Check expiration date
        try:
            exp_date = datetime.strptime(exp_str, "%Y%m%d").date()
            if datetime.now().date() > exp_date:
                return False, {"reason": "expired", "tier": "FREE", "expires": str(exp_date)}
        except ValueError:
            return False, {"reason": "invalid_date", "tier": "FREE"}

        # Check org binding if key is not wildcard ANY and caller supplied org_id
        if key_org != "ANY" and org_id:
            caller_org = _normalize_org(org_id)
            if caller_org != key_org:
                return False, {
                    "reason": f"org_mismatch (bound to {key_org})",
                    "tier": "FREE",
                }

        return True, {
            "tier": "PRO",
            "license_type": "COMMERCIAL_SIGNED",
            "bound_org": key_org,
            "expires": f"{exp_str[:4]}-{exp_str[4:6]}-{exp_str[6:8]}",
        }

    return False, {"reason": "unrecognized_key", "tier": "FREE"}

