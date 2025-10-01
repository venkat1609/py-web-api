from fastapi import APIRouter, HTTPException, Depends
from app.db.mongo import db
from bson import ObjectId
from datetime import datetime
from app.routes.auth import get_current_user

router = APIRouter()
collection = db["connections"]
users = db["users"]


def to_object_id(id_str: str):
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid ObjectId: {id_str}")



# ----------------------
# Get Friends List
# ----------------------
@router.get("")
async def get_friends(current_user: dict = Depends(get_current_user)):
    user_oid = current_user["_id"]

    cursor = collection.find(
        {
            "$or": [{"requesterId": user_oid}, {"recipientId": user_oid}],
            "status": "accepted",
        }
    )

    friends = []
    async for doc in cursor:
        friend_oid = (
            doc["recipientId"] if doc["requesterId"] == user_oid else doc["requesterId"]
        )
        user = await users.find_one({"_id": friend_oid})
        if user:
            friends.append(
                {
                    "userId": str(user["_id"]),
                    "user_name": user.get("user_name"),
                    "first_name": user.get("first_name"),
                    "last_name": user.get("last_name"),
                    "email": user.get("email"),
                }
            )
    return friends

# ----------------------
# Send Friend Request
# ----------------------
@router.post("/send_request")
async def send_friend_request(
    recipient_id: str, current_user: dict = Depends(get_current_user)
):
    requester_oid = current_user["_id"]
    recipient_oid = to_object_id(recipient_id)

    if requester_oid == recipient_oid:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a friend.")

    exists = await collection.find_one(
        {
            "$or": [
                {"requesterId": requester_oid, "recipientId": recipient_oid},
                {"requesterId": recipient_oid, "recipientId": requester_oid},
            ]
        }
    )
    if exists:
        return {"message": "Friend request or relationship already exists."}

    await collection.insert_one(
        {
            "requesterId": requester_oid,
            "recipientId": recipient_oid,
            "status": "pending",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
    )
    return {"message": "Friend request sent."}


# ----------------------
# Accept Friend Request
# ----------------------
@router.post("/accept_request")
async def accept_friend_request(
    requester_id: str, current_user: dict = Depends(get_current_user)
):
    recipient_oid = current_user["_id"]
    requester_oid = to_object_id(requester_id)

    result = await collection.update_one(
        {
            "requesterId": requester_oid,
            "recipientId": recipient_oid,
            "status": "pending",
        },
        {"$set": {"status": "accepted", "updatedAt": datetime.utcnow()}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No matching pending request.")
    return {"message": "Friend request accepted."}


# ----------------------
# Reject Friend Request
# ----------------------
@router.post("/reject_request")
async def reject_friend_request(
    requester_id: str, current_user: dict = Depends(get_current_user)
):
    recipient_oid = current_user["_id"]
    requester_oid = to_object_id(requester_id)

    await collection.update_one(
        {
            "requesterId": requester_oid,
            "recipientId": recipient_oid,
            "status": "pending",
        },
        {"$set": {"status": "rejected", "updatedAt": datetime.utcnow()}},
    )
    return {"message": "Friend request rejected."}


# ----------------------
# Remove Friend
# ----------------------
@router.delete("/remove_request")
async def remove_friend(friend_id: str, current_user: dict = Depends(get_current_user)):
    user_oid = current_user["_id"]
    friend_oid = to_object_id(friend_id)

    result = await collection.delete_one(
        {
            "$or": [
                {
                    "requesterId": user_oid,
                    "recipientId": friend_oid,
                    "status": "accepted",
                },
                {
                    "requesterId": friend_oid,
                    "recipientId": user_oid,
                    "status": "accepted",
                },
            ]
        }
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No active friendship found.")
    return {"message": "Friend removed."}



# ----------------------
# Get Pending Requests
# ----------------------
@router.get("/pending_request")
async def get_pending_requests(current_user: dict = Depends(get_current_user)):
    user_oid = current_user["_id"]

    cursor = collection.find(
        {
            "$or": [{"requesterId": user_oid}, {"recipientId": user_oid}],
            "status": "pending",
        }
    )

    requests = []
    async for doc in cursor:
        is_sent = doc["requesterId"] == user_oid
        other_user_id = doc["recipientId"] if is_sent else doc["requesterId"]
        other_user = await users.find_one({"_id": other_user_id})

        if other_user:
            requests.append(
                {
                    "direction": "sent" if is_sent else "received",
                    "userId": str(other_user["_id"]),
                    "email": other_user.get("email"),
                    "first_name": other_user.get("first_name"),
                    "status": doc["status"],
                }
            )
    return requests

