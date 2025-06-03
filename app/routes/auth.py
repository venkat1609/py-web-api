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

router = APIRouter()
security = HTTPBasic()
bearer_scheme = HTTPBearer()
collection = db["users"]


@router.post("/register")
async def register(user: User):
    existing_user = await collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = hash_password(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed,
        "age": user.age,
    }

    await collection.insert_one(user_data)
    return {"message": "User registered successfully"}


@router.get("/users")
async def get_all_users():
    users = []
    async for user in collection.find({}, {"_id": 0, "hashed_password": 0}):
        users.append(user)
    return users


@router.post("/login", response_model=Token)
async def login(credentials: HTTPBasicCredentials = Depends()):
    user = await collection.find_one({"username": credentials.username})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/current_user")
async def current_user(current_user: dict = Depends(get_current_user)):
    return {
        "user": {
            "username": current_user["username"],
            "email": current_user["email"],
            "age": current_user["age"],
        }
    }
