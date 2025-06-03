from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import quote_plus
import os

MONGO_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGO_URI)
print("Connected to MongoDB", MONGO_URI)

db = client["finance_app"]
users_collection = db["users"]

app = FastAPI()
security = HTTPBasic()
bearer_scheme = HTTPBearer()


class User(BaseModel):
    username: str
    age: int
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# JWT Configuration
SECRET_KEY = "your-secret-key"  # Use environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- Get current user from JWT ---
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials  # Correct way to get the token from Bearer scheme
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        user = await users_collection.find_one({"username": username})
        if not user:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception


# --- Routes ---
@app.post("/register")
async def register(user: User):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = hash_password(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed,
        "age": user.age,
    }

    await users_collection.insert_one(user_data)
    return {"message": "User registered successfully"}


@app.get("/users")
async def get_all_users():
    users = []
    async for user in users_collection.find(
        {}, {"_id": 0, "hashed_password": 0}
    ):  # hide sensitive info
        users.append(user)
    return users


@app.post("/login", response_model=Token)
async def login(credentials: HTTPBasicCredentials = Depends()):
    user = await users_collection.find_one({"username": credentials.username})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/current_user")
async def current_user(current_user: dict = Depends(get_current_user)):
    return {
        "user": {
            "username": current_user["username"],
            "email": current_user["email"],
            "age": current_user["age"],
        }
    }
