from fastapi import APIRouter, HTTPException, status, Depends, Body, Path
from app.models.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionOut,
    TransactionRequest
)
from app.db.mongo import db
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict
from app.utils.helpers import fix_id
from app.routes.auth import get_current_user  # 👈 New import

router = APIRouter()
collection = db["transactions"]


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    tx: TransactionCreate, current_user: str = Depends(get_current_user)
):

    now = datetime.utcnow()
    data = tx.dict()
    data["user_id"] = current_user["_id"]
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


@router.get("/{tx_id}")
async def get_transaction(tx_id: str, current_user: str = Depends(get_current_user)):
    doc = await collection.find_one({"_id": ObjectId(tx_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return fix_id(doc)


@router.post("/filter", response_model=List[TransactionOut])
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

    # Filter by different user_id (admin usage maybe)
    if "user_id" in filters:
        try:
            query["user_id"] = ObjectId(filters["user_id"])
        except:
            raise HTTPException(status_code=400, detail="Invalid user_id")

    cursor = collection.find(fix_id(query)).sort("date", -1)
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

    query = {"_id": txn_object_id, "user_id": ObjectId(current_user["_id"])}
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
    txn_id: str = Path(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        txn_object_id = ObjectId(txn_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    query = {"_id": txn_object_id, "user_id": ObjectId(current_user["_id"])}
    result = await collection.delete_one(query)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"message": "Transaction deleted successfully"}
