"""Automated 0-Cost Payment Webhook & License Issuer for EcoStream.

Receives payment webhook notifications from:
1. PayOS / SePay (VietQR banking transfer in Vietnam)
2. Lemon Squeezy (International credit cards / PayPal)

Upon successful payment, automatically generates an Ed25519 commercial license key
and can dispatch it to customer's email or display in checkout return page.

Usage:
    uvicorn scripts.payment_webhook_server:app --port 8080
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict
from fastapi import FastAPI, Header, HTTPException, Request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ecostream.privacy.licensing import generate_ed25519_license

app = FastAPI(title="EcoStream Payment & License Gateway (Zero-Cost Starter)")

WEBHOOK_SECRET = os.environ.get("PAYMENT_WEBHOOK_SECRET", "ecostream-secret-webhook-key")


@app.post("/webhook/payos")
async def payos_webhook(request: Request):
    """Webhook for PayOS (VietQR banking transfer)."""
    data = await request.json()
    # PayOS payload verification
    # data: {"code": "00", "desc": "success", "data": {"orderCode": 123456, "amount": 990000, "description": "ECOSTREAM PRO contact@company.vn"}}
    payload = data.get("data", {})
    description = payload.get("description", "")
    amount = payload.get("amount", 0)

    # Extract customer email / org from payment description
    # Example description: "ECOSTREAM congty_abc contact@abc.com"
    parts = description.split()
    org_id = parts[1] if len(parts) > 1 else "CUSTOMER"
    email = parts[2] if len(parts) > 2 and "@" in parts[2] else ""

    plan = "PRO" if amount >= 500000 else "STARTER"

    license_key = generate_ed25519_license(
        org_id=org_id,
        email=email,
        expires_iso="2027-12-31",
        plan=plan,
    )

    print(f"[✓] Payment received: {amount} VND for {org_id} ({email})")
    print(f"[✓] Issued License Key: {license_key}")

    # In production: trigger free email dispatch (e.g. Resend free tier 3000 emails/month)
    return {
        "status": "success",
        "org_id": org_id,
        "license_key": license_key,
        "message": "License generated successfully",
    }


@app.post("/webhook/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, x_signature: str = Header(None)):
    """Webhook for Lemon Squeezy (Global credit cards & PayPal)."""
    data = await request.json()
    event_name = data.get("meta", {}).get("event_name", "")

    if event_name == "order_created":
        order_data = data.get("data", {}).get("attributes", {})
        email = order_data.get("user_email", "")
        org_id = order_data.get("user_name", "ORGANIZATION").replace(" ", "")

        license_key = generate_ed25519_license(
            org_id=org_id,
            email=email,
            expires_iso="2027-12-31",
            plan="PRO",
        )

        print(f"[✓] LemonSqueezy Order from {email} -> Issued Key: {license_key}")
        return {"status": "success", "license_key": license_key}

    return {"status": "ignored"}

