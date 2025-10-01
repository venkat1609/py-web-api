from fastapi import APIRouter, HTTPException, status, Depends, Body, Path
from app.models.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionRequest,
)
from app.db.mongo import db
from bson import ObjectId
from datetime import datetime
from typing import List
from app.utils.helpers import fix_id
from app.routes.auth import get_current_user  # 👈 New import
from app.utils.enums import TransactionStatus

router = APIRouter()
collection = db["transactions"]

@router.get("")
async def list_transactions(current_user: str = Depends(get_current_user)):
    cursor = collection.find().sort("date", -1)

    results = []
    async for doc in cursor:
        results.append(fix_id(doc))
    return results



@router.post(
    "/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    tx: TransactionCreate, current_user: str = Depends(get_current_user)
):

    now = datetime.utcnow()
    data = tx.dict()
    data["userId"] = ObjectId(current_user["_id"])
    data["createdAt"] = now
    data["updatedAt"] = now

    result = await collection.insert_one(data)
    created = await collection.find_one({"_id": result.inserted_id})
    return fix_id(created)



@router.put("/{txn_id}")
async def update_transaction(
    txn_id: str = Path(...),
    payload: TransactionUpdate = Body(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        txn_object_id = ObjectId(txn_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    print(current_user)

    query = {"_id": txn_object_id, "userId": current_user["_id"]}
    update = {"$set": {k: v for k, v in payload.dict().items() if v is not None}}

    result = await collection.update_one(query, update)
    print(result)

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404, detail="Transaction not found or no changes made"
        )

    updated = await collection.find_one({"_id": txn_object_id})
    return fix_id(updated)


@router.delete("/{txn_id}")
async def delete_transaction(
    txn_id: str = Path(...), current_user: dict = Depends(get_current_user)
):
    try:
        txn_object_id = ObjectId(txn_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    query = {"_id": txn_object_id, "userId": ObjectId(current_user["_id"])}
    result = await collection.delete_one(query)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"message": "Transaction deleted successfully"}


@router.get("/{txn_id}")
async def get_transaction(txn_id: str, current_user: str = Depends(get_current_user)):
    doc = await collection.find_one({"_id": ObjectId(txn_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return fix_id(doc)


@router.post("/filter", response_model=List[TransactionResponse])
async def filter_transactions(
    filters: TransactionRequest, current_user: str = Depends(get_current_user)
):
    query = {}

    # Filter by transaction ID (optional)
    if "id" in filters:
        try:
            query["_id"] = ObjectId(filters["id"])
        except:
            raise HTTPException(status_code=400, detail="Invalid txn_id")

    query["userId"] = ObjectId(current_user["_id"])

    cursor = collection.find(query).sort("date", -1)
    results = [fix_id(doc) async for doc in cursor]
    return results


@router.post("/expense_summary_by_category")
async def get_expense_summary_by_category(
    current_user: dict = Depends(get_current_user),
):
    exchange_rates_collection = db["exchange_rates"]

    rate_doc = await exchange_rates_collection.find_one(
        {"base": "usd"}, sort=[("fetched_at", -1)]
    )

    if not rate_doc:
        raise HTTPException(status_code=500, detail="Exchange rates not available.")

    rates = rate_doc["rates"]  # e.g., { "aed": 3.67, "inr": 83.2, ... }

    # 2. Get all user's expense transactions
    transactions_cursor = collection.find(
        {
            "type": "expense",
            "status": TransactionStatus.completed,
            "userId": ObjectId(current_user["_id"]),
        }
    )

    category_summary = {}

    async for tx in transactions_cursor:
        category_id = str(tx["category"])
        currency = tx["currency"].lower()
        amount = tx["amount"]

        rate = rates.get(currency)
        if rate is None or rate == 0:
            continue  # Skip unknown or invalid currencies

        amount_in_usd = amount / rate  # Convert to USD

        if category_id not in category_summary:
            category_summary[category_id] = {"totalAmount": 0, "count": 0}

        category_summary[category_id]["totalAmount"] += amount_in_usd
        category_summary[category_id]["count"] += 1
        category_summary[category_id]["currency"] = "usd"

    # 3. Format and sort result
    result = [{"category": cat_id, **data} for cat_id, data in category_summary.items()]
    result.sort(key=lambda x: x["totalAmount"], reverse=True)

    # Rename fields for cleaner response
    return result


@router.post("/overall_expense")
async def get_overall_expense(
    filters: dict = Body(default={}),
    current_user: dict = Depends(get_current_user),
):
    from_date_str = filters.get("from_date")
    to_date_str = filters.get("to_date")
    exchange_rates_collection = db["exchange_rates"]
    match_filter = {
        "type": "expense",
        "userId": ObjectId(current_user["_id"]),
    }

    if from_date_str:
        try:
            from_date = datetime.fromisoformat(from_date_str)
            match_filter["createdAt"] = {"$gte": from_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format.")

    if to_date_str:
        try:
            to_date = datetime.fromisoformat(to_date_str)
            if "createdAt" in match_filter:
                match_filter["createdAt"]["$lte"] = to_date
            else:
                match_filter["createdAt"] = {"$lte": to_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format.")

    # 1. Get latest exchange rates
    rate_doc = await exchange_rates_collection.find_one(
        {"base": "usd"}, sort=[("fetched_at", -1)]
    )

    if not rate_doc:
        raise HTTPException(status_code=500, detail="Exchange rates not available.")

    rates = rate_doc["rates"]  # e.g., { "aed": 3.67, "inr": 83.2, ... }

    # 2. Get filtered expense transactions
    transactions_cursor = collection.find(match_filter)

    category_summary = {"totalAmount": 0, "count": 0, "currency": "usd"}

    async for tx in transactions_cursor:
        currency = tx.get("currency", "usd").lower()
        amount = tx.get("amount", 0)

        rate = rates.get(currency)
        if rate is None or rate == 0:
            continue  # Skip unknown or invalid currencies

        amount_in_usd = amount / rate
        category_summary["totalAmount"] += amount_in_usd
        category_summary["count"] += 1

    return category_summary


@router.post("/balance_summary")
async def get_balance_summary(
    filters: dict = Body(default={}),
    current_user: dict = Depends(get_current_user),
):
    from_date_str = filters.get("from_date")
    to_date_str = filters.get("to_date")

    match_filter = {
        "userId": ObjectId(current_user["_id"]),
    }

    # Apply date range filter
    if from_date_str:
        try:
            from_date = datetime.fromisoformat(from_date_str)
            match_filter["createdAt"] = {"$gte": from_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format.")

    if to_date_str:
        try:
            to_date = datetime.fromisoformat(to_date_str)
            if "createdAt" in match_filter:
                match_filter["createdAt"]["$lte"] = to_date
            else:
                match_filter["createdAt"] = {"$lte": to_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format.")

    # Get latest USD exchange rates
    rate_doc = await db["exchange_rates"].find_one(
        {"base": "usd"}, sort=[("fetched_at", -1)]
    )
    if not rate_doc:
        raise HTTPException(status_code=500, detail="Exchange rates not available.")
    rates = rate_doc["rates"]

    income_total = 0.0
    expense_total = 0.0
    currency = "usd"

    cursor = collection.find(match_filter)

    async for tx in cursor:
        amount = tx.get("amount", 0)
        tx_type = tx.get("type")
        tx_currency = tx.get("currency", "usd").lower()

        rate = rates.get(tx_currency)
        if rate is None or rate == 0:
            continue

        amount_in_usd = amount / rate

        if tx_type == "income":
            income_total += amount_in_usd
        elif tx_type == "expense":
            expense_total += amount_in_usd

    balance = income_total - expense_total

    return {
        "income": round(income_total, 2),
        "expense": round(expense_total, 2),
        "balance": round(balance, 2),
        "currency": currency,
    }
