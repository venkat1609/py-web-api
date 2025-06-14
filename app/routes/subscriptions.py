from fastapi import APIRouter, HTTPException, status, Depends, Body, Path
from app.models.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionRequest,
)
from app.db.mongo import db
from bson import ObjectId
from datetime import datetime
from typing import List
from app.utils.helpers import fix_id
from app.routes.auth import get_current_user  # 👈 New import

router = APIRouter()
collection = db["subscriptions"]


@router.post(
    "/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    tx: SubscriptionCreate, current_user: str = Depends(get_current_user)
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
async def list_subscriptions(current_user: str = Depends(get_current_user)):
    cursor = collection.find().sort("date", -1)

    results = []
    async for doc in cursor:
        results.append(fix_id(doc))
    return results


@router.put("/{sub_id}")
async def update_subscription(
    sub_id: str = Path(...),
    payload: SubscriptionUpdate = Body(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        sub_object_id = ObjectId(sub_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid subscription ID")

    query = {"_id": sub_object_id, "userId": ObjectId(current_user["_id"])}
    update = {"$set": {k: v for k, v in payload.dict().items() if v is not None}}

    result = await collection.update_one(query, update)

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404, detail="Subscription not found or no changes made"
        )

    updated = await collection.find_one({"_id": sub_object_id})
    return fix_id(updated)


@router.delete("/{sub_id}")
async def delete_subscription(
    sub_id: str = Path(...), current_user: dict = Depends(get_current_user)
):
    try:
        sub_object_id = ObjectId(sub_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid subscription ID")

    query = {"_id": sub_object_id, "userId": ObjectId(current_user["_id"])}
    result = await collection.delete_one(query)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"message": "Subscription deleted successfully"}


@router.get("/getSubscriptionById/{sub_id}")
async def get_subscription(sub_id: str, current_user: str = Depends(get_current_user)):
    doc = await collection.find_one({"_id": ObjectId(sub_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return fix_id(doc)


@router.post("/filter", response_model=List[SubscriptionResponse])
async def filter_subscriptions(
    filters: SubscriptionRequest, current_user: str = Depends(get_current_user)
):
    query = {}

    # Filter by subscription ID (optional)
    if "id" in filters:
        try:
            query["_id"] = ObjectId(filters["id"])
        except:
            raise HTTPException(status_code=400, detail="Invalid sub_id")

    # Filter by different userId (admin usage maybe)
    if "userId" in filters:
        try:
            query["userId"] = ObjectId(filters["userId"])
        except:
            raise HTTPException(status_code=400, detail="Invalid userId")

    cursor = collection.find(query).sort("date", -1)
    results = [fix_id(doc) async for doc in cursor]
    return results
