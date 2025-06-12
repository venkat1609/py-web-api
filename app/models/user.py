from typing import Optional
from pydantic import BaseModel, EmailStr


class UserInDB(BaseModel):
    username: str
    age: int
    email: EmailStr
    hashed_password: str

    class Config:
        orm_mode = True


# Model used in DB (with password)
class UserInDB(BaseModel):
    id: str
    username: str
    email: EmailStr
    age: int
    password: str


# Model returned in API response (no password)
class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    age: int


class User(BaseModel):
    username: str
    age: int
    email: str
    password: str


class UserBase(BaseModel):
    username: str
    email: EmailStr
    age: int


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: str


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str
