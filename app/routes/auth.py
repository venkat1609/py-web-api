from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from fastapi.responses import RedirectResponse
from app.models.user import User, UserOut, LoginRequest, UserResponse
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, get_current_user
from app.db.mongo import db
from app.utils.helpers import fix_id  # assuming you use the helper
from typing import Union, List
from pydantic import BaseModel
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os

router = APIRouter()
security = HTTPBasic()
bearer_scheme = HTTPBearer()
collection = db["users"]


@router.post("/register")
async def register(user: User):
    existing_user = await collection.find_one({"user_name": user.user_name})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check for existing email
    existing_email = await collection.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    user_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "user_name": user.user_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "date_of_birth": user.date_of_birth,
        "profile_image": user.profile_image,
        "is_phone_verified": user.is_phone_verified,
        "is_email_verified": user.is_email_verified,
        "hashed_password": hashed_password,
    }

    await collection.insert_one(user_data)

    access_token = create_access_token(data={"sub": user_data["user_name"]})

    user = {
        "id": str(user_data["_id"]),
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "user_name": user_data["user_name"],
        "email": user_data["email"],
        "phone_number": user_data["phone_number"],
        "date_of_birth": user_data["date_of_birth"],
        "profile_image": user_data["profile_image"],
        "is_phone_verified": user_data["is_phone_verified"],
        "is_email_verified": user_data["is_email_verified"],
        "access_token": access_token,
    }

    return user


@router.post("/login")
async def login(credentials: LoginRequest):
    user = await collection.find_one({"user_name": credentials.user_name})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["user_name"]})

    user_data = {
        "id": str(user["_id"]),
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "user_name": user["user_name"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "date_of_birth": user["date_of_birth"],
        "profile_image": user["profile_image"],
        "is_phone_verified": user["is_phone_verified"],
        "is_email_verified": user["is_email_verified"],
        "access_token": access_token,
    }

    return user_data


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


client = os.getenv("GOOGLE_CLIENT_ID")


class TokenPayload(BaseModel):
    id_token: str


@router.post("/google/token")
async def google_login_token(payload: TokenPayload):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), client
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    # Check for existing email
    existing_email = await collection.find_one({"email": idinfo.get("email")})
    if existing_email:
        user = await collection.find_one({"email": existing_email["email"]})

        access_token = create_access_token(data={"sub": user["email"]})

        user_data = {
            "id": str(user["_id"]),
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "user_name": user["user_name"],
            "email": user["email"],
            "phone_number": user["phone_number"],
            "date_of_birth": user["date_of_birth"],
            "profile_image": user["profile_image"],
            "is_phone_verified": user["is_phone_verified"],
            "is_email_verified": user["is_email_verified"],
            "access_token": access_token,
        }

        return user_data

    else:
        user_data = {
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "profile_image": idinfo.get("picture"),
            "first_name": idinfo.get("given_name"),
            "last_name": idinfo.get("family_name"),
            "user_name": None,
            "phone_number": None,
            "date_of_birth": None,
            "is_phone_verified": False,
            "is_email_verified": True,
            "hashed_password": None,
        }

        await collection.insert_one(user_data)

        access_token = create_access_token(data={"sub": user_data["email"]})

        user = {
            "id": str(user_data["_id"]),
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "user_name": user_data["user_name"],
            "email": user_data["email"],
            "phone_number": user_data["phone_number"],
            "date_of_birth": user_data["date_of_birth"],
            "profile_image": user_data["profile_image"],
            "is_phone_verified": user_data["is_phone_verified"],
            "is_email_verified": user_data["is_email_verified"],
            "access_token": access_token,
        }

        return user
