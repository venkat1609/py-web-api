from typing import Optional
from pydantic import BaseModel, EmailStr


# Model returned in API response (no password)
class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    user_name: str
    email: EmailStr
    phone_number: str
    date_of_birth: str
    profile_image: str
    is_phone_verified: bool
    is_email_verified: bool


class User(BaseModel):
    email: EmailStr
    password: str


class UserBase(BaseModel):
    email: EmailStr

class UserOut(UserBase):
    id: str

class LoginRequest(BaseModel):
    email: str
    password: str
