from fastapi import APIRouter, HTTPException, status
from app.models.transaction import TransactionCreate, TransactionUpdate, TransactionOut
from app.db.mongo import db, fix_id
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter(prefix="/transactions", tags=["Transactions"])

collection = db["transactions"]


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(tx: TransactionCreate):
    now = datetime.utcnow()
    data = tx.dict()
    data["user_id"] = ObjectId(tx.user_id)
    data["createdAt"] = now
    data["updatedAt"] = now
    result = await collection.insert_one(data)
    created = await collection.find_one({"_id": result.inserted_id})
    return fix_id(created)


@router.get("/", response_model=List[TransactionOut])
async def list_transactions():
    cursor = collection.find().sort("date", -1)
    results = []
    async for doc in cursor:
        results.append(fix_id(doc))
    return results


@router.get("/{tx_id}", response_model=TransactionOut)
async def get_transaction(tx_id: str):
    doc = await collection.find_one({"_id": ObjectId(tx_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return fix_id(doc)


@router.put("/{tx_id}", response_model=TransactionOut)
async def update_transaction(tx_id: str, update: TransactionUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow()

    result = await collection.update_one(
        {"_id": ObjectId(tx_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")

    doc = await collection.find_one({"_id": ObjectId(tx_id)})
    return fix_id(doc)


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(tx_id: str):
    result = await collection.delete_one({"_id": ObjectId(tx_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return
