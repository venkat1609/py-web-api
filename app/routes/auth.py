from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from app.models.user import User, UserOut, LoginRequest, UserResponse
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, get_current_user
from app.db.mongo import db
from app.utils.helpers import fix_id  # assuming you use the helper
from typing import Union, List

router = APIRouter()
security = HTTPBasic()
bearer_scheme = HTTPBearer()
collection = db["users"]


@router.post("/register")
async def register(user: User):
    existing_user = await collection.find_one({"user_name": user["user_name"]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check for existing email
    existing_email = await collection.find_one({"email": user["email"]})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    user_data = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "user_name": user["user_name"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "date_of_birth": user["date_of_birth"],
        "profile_image": user["profile_image"],
        "is_phone_verified": user["is_phone_verified"],
        "is_email_verified": user["is_email_verified"],
        "hashed_password": hashed_password,
    }

    await collection.insert_one(user_data)

    access_token = create_access_token(data={"sub": user_data["userName"]})

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


async def get_all_users_from_db():
    users_raw = await db["users"].find().to_list(length=100)
    users = []

    for user in users_raw:
        users.append(
            UserResponse(
                id=str(user["_id"]),
                first_name=user["first_name"],
                last_name=user["last_name"],
                username=user["user_name"],
                email=user["email"],
                phone_number=user["phone_number"],
                date_of_birth=user["date_of_birth"],
                profile_image=user["profile_image"],
                is_phone_verified=user["is_phone_verified"],
                is_email_verified=user["is_email_verified"],
            )
        )

    return users


@router.get("/users", response_model=List[UserResponse])
async def get_users():
    users = await get_all_users_from_db()
    # Exclude password from response
    return [UserResponse(**user.dict(exclude={"password"})) for user in users]


@router.post("/login")
async def login(credentials: LoginRequest):
    user = await collection.find_one({"user_name": credentials.user_name})
    if not user or not verify_password(
        credentials.password, user["hashed_password"]
    ):
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
