"""CLI Tool for Vendor to Issue Asymmetric Ed25519 Commercial License Keys.

Usage:
    # Issue a 1-year Pro license for an enterprise:
    python scripts/generate_license_key.py --org "ecogarment-vn" --email "ceo@ecogarment.vn" --expires 2027-12-31 --plan PRO

    # Issue an Enterprise license with custom features:
    python scripts/generate_license_key.py --org "vinamilk" --plan ENTERPRISE --expires 2028-12-31
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ecostream.privacy.licensing import (
    generate_ed25519_license,
    verify_commercial_license,
    generate_commercial_license,
)


def main():
    parser = argparse.ArgumentParser(description="EcoStream Commercial Asymmetric License Generator")
    parser.add_argument("--org", required=True, help="Organization ID or Tax Code (e.g., ecogarment-vn or 0101234567)")
    parser.add_argument("--email", default="", help="Customer contact email")
    parser.add_argument("--expires", default="2027-12-31", help="Expiration date in YYYY-MM-DD format (default: 2027-12-31)")
    parser.add_argument("--plan", default="PRO", choices=["PRO", "ENTERPRISE"], help="License tier plan")
    parser.add_argument("--legacy", action="store_true", help="Generate legacy ECO1 HMAC format instead of Ed25519")
    args = parser.parse_args()

    if args.legacy:
        exp_compact = args.expires.replace("-", "")
        key = generate_commercial_license(args.org, exp_compact)
    else:
        key = generate_ed25519_license(
            org_id=args.org,
            email=args.email,
            expires_iso=args.expires,
            plan=args.plan,
        )

    ok, meta = verify_commercial_license(key, args.org)

    print("=" * 72)
    print("  ECOSTREAM — COMMERCIAL ASYMMETRIC LICENSE GENERATOR (ED25519)")
    print("=" * 72)
    print(f"  Organization / MST : {args.org} (Normalized: {meta.get('bound_org')})")
    print(f"  Contact Email      : {args.email or 'N/A'}")
    print(f"  Tier Plan          : {meta.get('tier')}")
    print(f"  License Type       : {meta.get('license_type')}")
    print(f"  Expiration Date    : {meta.get('expires')}")
    print(f"  Features Unlocked  : {', '.join(meta.get('features', []))}")
    print(f"  Verification Check : {'✓ VALID (100% Offline Verified)' if ok else '✗ INVALID'}")
    print("-" * 72)
    print("  CUSTOMER LICENSE KEY:")
    print(f"  {key}")
    print("=" * 72)


if __name__ == "__main__":
    main()
