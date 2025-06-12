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


@router.get("/expense-summary-by-category")
async def get_expense_summary_by_category(
    current_user: dict = Depends(get_current_user),
):

    pipeline = [
        {"$match": {"type": "expense"}},
        {
            "$group": {
                "_id": "$categoryId",
                "totalAmount": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"totalAmount": -1}},  # optional: sort by total descending
    ]

    results = [doc async for doc in collection.aggregate(pipeline)]  # ✅ Correct for Motor

    # Rename fields for cleaner response
    return [
        {
            "category": item["_id"],
            "totalAmount": item["totalAmount"],
            "count": item["count"],
        }
        for item in results
    ]


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
