"""CLI Tool for Vendor to Issue Offline Commercial License Keys for SMEs.

Usage:
    python scripts/generate_license_key.py --org "ecogarment-vn" --expires 20271231
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ecostream.privacy.licensing import generate_commercial_license, verify_commercial_license


def main():
    parser = argparse.ArgumentParser(description="EcoStream Commercial Offline License Generator")
    parser.add_argument("--org", required=True, help="Organization ID or Tax Code (e.g., ecogarment-vn or 0101234567)")
    parser.add_argument("--expires", default="20271231", help="Expiration date in YYYYMMDD format (default: 20271231)")
    args = parser.parse_args()

    key = generate_commercial_license(args.org, args.expires)
    ok, meta = verify_commercial_license(key, args.org)

    print("=" * 64)
    print("  ECOSTREAM — COMMERCIAL OFFLINE LICENSE KEY GENERATOR")
    print("=" * 64)
    print(f"  Organization / MST : {args.org} (Normalized: {meta.get('bound_org')})")
    print(f"  Expiration Date    : {meta.get('expires')}")
    print(f"  Verification Check : {'VALID' if ok else 'INVALID'}")
    print("-" * 64)
    print(f"  LICENSE KEY        : {key}")
    print("=" * 64)


if __name__ == "__main__":
    main()

