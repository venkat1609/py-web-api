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

# In-memory user store
fake_users_db = {}

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
def get_current_user(
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
        if not username or username not in fake_users_db:
            raise credentials_exception
        return fake_users_db[username]
    except JWTError:
        raise credentials_exception


# --- Routes ---
@app.post("/register")
def register(user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = hash_password(user.password)
    fake_users_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed,
        "age": user.age,
    }
    return {"message": "User registered successfully"}


@app.get("/users")
def get_all_users():
    return fake_users_db


@app.post("/login", response_model=Token)
def login(credentials: HTTPBasicCredentials = Depends()):
    user = fake_users_db.get(credentials.username)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
