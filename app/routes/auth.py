from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from app.schemas.user import User, Token
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, get_current_user
from app.db.mongo import db
from app.utils.helpers import fix_id  # assuming you use the helper
from typing import Union, List
from app.schemas.user import UserOut, LoginRequest, UserResponse, UserInDB

router = APIRouter()
security = HTTPBasic()
bearer_scheme = HTTPBearer()
collection = db["users"]


@router.post("/register")
async def register(user: User):
    existing_user = await collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check for existing email
    existing_email = await collection.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed,
        "age": user.age,
    }

    await collection.insert_one(user_data)

    access_token = create_access_token(data={"sub": user_data["username"]})

    user = {
        "id": str(user_data["_id"]),
        "username": user_data["username"],
        "email": user_data["email"],
        "age": user_data["age"],
        "access_token": access_token,
        "token_type": "bearer",
    }

    return user


def mongo_to_user(user):
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "age": user["age"],
    }


async def get_all_users_from_db():
    users_raw = await db["users"].find().to_list(length=100)
    users = []

    for user in users_raw:
        users.append(
            UserResponse(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"],
                age=user["age"],
            )
        )

    return users


@router.get("/users", response_model=List[UserResponse])
async def get_users():
    users = await get_all_users_from_db()
    # Exclude password from response
    return [UserResponse(**user.dict(exclude={"password"})) for user in users]


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest):
    user = await collection.find_one({"username": credentials.username})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["username"]})

    user_data = {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "age": user["age"],
        "access_token": access_token,
        "token_type": "bearer",
    }

    return user_data


@router.get("/current_user", response_model=UserOut)
async def current_user(current_user: dict = Depends(get_current_user)):
    return fix_id(current_user)
