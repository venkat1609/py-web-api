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

router = APIRouter()
collection = db["transactions"]


@router.post(
    "/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    tx: TransactionCreate, current_user: str = Depends(get_current_user)
):

    now = datetime.utcnow()
    data = tx.dict()
    data["userId"] = current_user["_id"]
    data["createdAt"] = now
    data["updatedAt"] = now

    result = await collection.insert_one(data)
    created = await collection.find_one({"_id": result.inserted_id})
    return fix_id(created)


@router.get("/")
async def list_transactions(current_user: str = Depends(get_current_user)):
    cursor = collection.find().sort("date", -1)

    results = []
    async for doc in cursor:
        results.append(fix_id(doc))
    return results


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

    query = {"_id": txn_object_id, "userId": ObjectId(current_user["_id"])}
    update = {"$set": {k: v for k, v in payload.dict().items() if v is not None}}

    result = await collection.update_one(query, update)

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


@router.get("/getTransactionById/{tx_id}")
async def get_transaction(tx_id: str, current_user: str = Depends(get_current_user)):
    doc = await collection.find_one({"_id": ObjectId(tx_id)})
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

    # Filter by different userId (admin usage maybe)
    if "userId" in filters:
        try:
            query["userId"] = ObjectId(filters["userId"])
        except:
            raise HTTPException(status_code=400, detail="Invalid userId")

    cursor = collection.find(query).sort("date", -1)
    results = [fix_id(doc) async for doc in cursor]
    return results


@router.get("/expense-summary-by-category")
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

    print(current_user)

    # 2. Get all user's expense transactions
    transactions_cursor = collection.find(
        {"type": "expense", "userId": ObjectId(current_user["_id"])}
    )

    category_summary = {}

    async for tx in transactions_cursor:
        category_id = str(tx["categoryId"])
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
