from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import (
    HTTPBasic,
    HTTPBearer,
)
from app.models.user import User, UserOut, LoginRequest, UserResponse
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, get_current_user
from app.db.mongo import db
from app.utils.helpers import fix_id  # assuming you use the helper
from typing import Union, List
import re
from pymongo import ASCENDING

router = APIRouter()
security = HTTPBasic()
bearer_scheme = HTTPBearer()
collection = db["users"]


@router.get("/search", response_model=List[UserResponse])
async def search_users(
    query: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
):
    cursor = collection.find(
        {
            "$or": [
                {"user_name": query},
                {"email": query},
            ]
        }
    ).sort("user_name", ASCENDING)

    result = []
    async for user in cursor:
        result.append(
            UserResponse(
                id=str(user["_id"]),
                user_name=user.get("user_name", ""),
                email=user.get("email", ""),
                first_name=user.get("first_name", ""),
                last_name=user.get("last_name", ""),
                phone_number=user.get("phone_number", ""),
                date_of_birth=user.get("date_of_birth", ""),
                is_email_verified=user.get("is_email_verified", False),
                is_phone_verified=user.get("is_phone_verified", False),
                profile_image=user.get("profile_image"),
            )
        )

    return result


@router.get("/current_user", response_model=UserOut)
async def current_user(current_user: dict = Depends(get_current_user)):
    return fix_id(current_user)

@router.get("/users", response_model=List[UserResponse])
async def get_users():
    users = await get_all_users_from_db()
    # Exclude password from response
    return [UserResponse(**user.dict(exclude={"password"})) for user in users]


async def get_all_users_from_db():
    users_raw = await db["users"].find().to_list(length=100)
    users = []

    for user in users_raw:
        users.append(
            UserResponse(
                id=str(user["_id"]),
                first_name=user["first_name"],
                last_name=user["last_name"],
                user_name=user["user_name"],
                email=user["email"],
                phone_number=user["phone_number"],
                date_of_birth=user["date_of_birth"],
                profile_image=user["profile_image"],
                is_phone_verified=user["is_phone_verified"],
                is_email_verified=user["is_email_verified"],
            )
        )

    return users
