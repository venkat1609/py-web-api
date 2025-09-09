from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Dict, Any
from app.core.jwt import get_current_user
from app.db.mongo import db
from bson import ObjectId
from datetime import datetime
import os

import stripe

router = APIRouter()


class CheckoutSessionRequest(BaseModel):
    priceId: str
    mode: str  # "subscription" for subscriptions


@router.post("/create-checkout-session")
async def create_checkout_session(
    session_req: CheckoutSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    if session_req.mode != "subscription":
        raise HTTPException(status_code=400, detail="Invalid mode")

    # Ensure API key per-request
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(
            status_code=500, detail="STRIPE_SECRET_KEY not configured in environment."
        )

    try:
        print("Creating checkout session for user:", current_user.get("customer_id"))

        if not current_user.get("customer_id"):
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": session_req.priceId, "quantity": 1}],
                customer_email=current_user.get("email"),
                client_reference_id=str(current_user.get("_id")),
                success_url="http://localhost:3000/payment/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="http://localhost:3000/payment/cancel",
            )
        else:
            checkout_session = stripe.checkout.Session.create(
                customer=current_user.get("customer_id"),
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": session_req.priceId, "quantity": 1}],
                client_reference_id=str(current_user.get("_id")),
                success_url="http://localhost:3000/payment/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="http://localhost:3000/payment/cancel",
            )

        return {"id": checkout_session.id, "url": checkout_session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e.user_message}")


class CheckoutSessionRetrieve(BaseModel):
    session_id: str = Field(
        ..., alias="sessionId", description="Stripe Checkout Session ID"
    )

    class Config:
        allow_population_by_field_name = True


@router.post("/checkout-success")
async def checkout_success(
    payload: CheckoutSessionRetrieve = Body(...),
    current_user: dict = Depends(get_current_user),
):
    # Configure Stripe per-request
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(
            status_code=500, detail="STRIPE_SECRET_KEY not configured in environment."
        )

    # Retrieve session
    session_id = payload.session_id
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")

    # Ownership check via client_reference_id or email
    session_email = session.get("customer_email") or (
        session.get("customer_details") or {}
    ).get("email")
    session_client_ref = session.get("client_reference_id")
    user_email = current_user.get("email")
    if session_client_ref and str(current_user.get("_id")) != str(session_client_ref):
        raise HTTPException(
            status_code=403, detail="Session does not belong to the current user"
        )
    if (
        (not session_client_ref)
        and session_email
        and user_email
        and (session_email.lower() != user_email.lower())
    ):
        raise HTTPException(
            status_code=403, detail="Session does not belong to the current user"
        )

    # Base response
    result: Dict[str, Any] = {
        "id": session.get("id"),
        "status": session.get("status"),
        "payment_status": session.get("payment_status"),
        "mode": session.get("mode"),
        "customer_email": session_email,
        "client_reference_id": session_client_ref,
        "subscription": session.get("subscription"),
    }

    # Persist in two collections when subscription is successful
    try:
        is_success = (session.get("status") == "complete") or (
            session.get("payment_status") in ("paid", "no_payment_required")
        )
        sub_id = session.get("subscription")
        if is_success and session.get("mode") == "subscription" and sub_id:
            # Retrieve subscription and extract key fields
            sub = None
            try:
                sub = stripe.Subscription.retrieve(sub_id)
                period_start_ts = (
                    sub.get("current_period_start")
                    if hasattr(sub, "get")
                    else getattr(sub, "current_period_start", None)
                )
                period_end_ts = (
                    sub.get("current_period_end")
                    if hasattr(sub, "get")
                    else getattr(sub, "current_period_end", None)
                )
                items = (
                    (sub.get("items") or {}).get("data", [])
                    if hasattr(sub, "get")
                    else getattr(sub, "items", None).data
                )
                item = items[0] if items else None
                price = (
                    (
                        item.get("price")
                        if isinstance(item, dict)
                        else getattr(item, "price", None)
                    )
                    if item
                    else None
                )
                # Find tier: product name
                product_ref = (
                    (
                        price.get("product")
                        if isinstance(price, dict)
                        else getattr(price, "product", None)
                    )
                    if price
                    else None
                )
                tier = None
                try:
                    if isinstance(product_ref, str):
                        prod = stripe.Product.retrieve(product_ref)
                        tier = (
                            prod.get("name")
                            if hasattr(prod, "get")
                            else getattr(prod, "name", None)
                        )
                    elif isinstance(product_ref, dict):
                        tier = product_ref.get("name")
                except Exception:
                    # fallback to price nickname
                    tier = (
                        (
                            price.get("nickname")
                            if isinstance(price, dict)
                            else getattr(price, "nickname", None)
                        )
                        if price
                        else None
                    )
                amount_cents = (
                    (
                        price.get("unit_amount")
                        if isinstance(price, dict)
                        else getattr(price, "unit_amount", None)
                    )
                    if price
                    else None
                )
                currency = (
                    (
                        price.get("currency")
                        if isinstance(price, dict)
                        else getattr(price, "currency", None)
                    )
                    if price
                    else None
                )
                recurring = (
                    (
                        price.get("recurring")
                        if isinstance(price, dict)
                        else getattr(price, "recurring", None)
                    )
                    if price
                    else None
                )
                interval = (
                    (
                        recurring.get("interval")
                        if isinstance(recurring, dict)
                        else getattr(recurring, "interval", None)
                    )
                    if recurring
                    else None
                )
            except Exception:
                period_start_ts = None
                period_end_ts = None
                tier = None
                amount_cents = None
                currency = None
                interval = None

            starts_at = (
                datetime.utcfromtimestamp(period_start_ts)
                if isinstance(period_start_ts, (int, float))
                else None
            )
            ends_at = (
                datetime.utcfromtimestamp(period_end_ts)
                if isinstance(period_end_ts, (int, float))
                else None
            )
            amount = (
                (amount_cents / 100.0)
                if isinstance(amount_cents, (int, float))
                else None
            )
            is_recurring = bool(interval)

            uid = current_user.get("_id")
            if uid:
                cust_col = db["stripe_customers"]
                txn_col = db["stripe_transactions"]
                sess_id = session.get("id")

                # 1) Upsert single stripe_customer doc per user
                up_res = await cust_col.update_one(
                    {"user_id": ObjectId(str(uid))},
                    {
                        "$set": {
                            "session_id": sess_id,
                            "customer_id": session.get("customer"),
                            "tier": tier,
                            "amount": amount,
                            "currency": currency,
                            "starts_at": starts_at,
                            "ends_at": ends_at,
                            "is_recurring": is_recurring,
                            "interval": interval,
                            "status": (
                                (
                                    sub.get("status")
                                    if hasattr(sub, "get")
                                    else getattr(sub, "status", None)
                                )
                                if sub
                                else None
                            ),
                            "subscription_id": sub_id,
                            "updated_at": datetime.utcnow(),
                        },
                        "$setOnInsert": {"created_at": datetime.utcnow()},
                    },
                    upsert=True,
                )
                if up_res.upserted_id:
                    stripe_customer_id = up_res.upserted_id
                else:
                    existing_cust = await cust_col.find_one(
                        {"user_id": ObjectId(str(uid))}
                    )
                    stripe_customer_id = existing_cust["_id"] if existing_cust else None

                # 2) Upsert transaction by session_id (idempotent per session)
                try:
                    session_dict = session.to_dict()  # type: ignore[attr-defined]
                except Exception:
                    session_dict = {
                        "id": session.get("id"),
                        "status": session.get("status"),
                        "payment_status": session.get("payment_status"),
                        "mode": session.get("mode"),
                        "customer": session.get("customer"),
                    }
                try:
                    sub_dict = sub.to_dict() if sub else None  # type: ignore[attr-defined]
                except Exception:
                    sub_dict = None

                existing_txn = await txn_col.find_one({"session_id": sess_id})
                if existing_txn:
                    await txn_col.update_one(
                        {"_id": existing_txn["_id"]},
                        {
                            "$set": {
                                "session": session_dict,
                                "subscription": sub_dict,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
                    result["transaction_id"] = str(existing_txn["_id"])
                else:
                    txn_doc = {
                        "stripe_customer_id": stripe_customer_id,
                        "user_id": ObjectId(str(uid)),
                        "session_id": sess_id,
                        "session": session_dict,
                        "subscription": sub_dict,
                        "created_at": datetime.utcnow(),
                    }
                    txn_res = await txn_col.insert_one(txn_doc)
                    result["transaction_id"] = str(txn_res.inserted_id)

                # 3) Update user with key stripe fields
                await db["users"].update_one(
                    {"_id": ObjectId(str(uid))},
                    {
                        "$set": {
                            "customer_id": session.get("customer"),
                            "tier": tier,
                            "ends_at": ends_at,
                        }
                    },
                )

                if stripe_customer_id:
                    result["stripe_customer_id"] = str(stripe_customer_id)
    except Exception:
        # Do not block response on persistence hiccups
        pass

    return result
