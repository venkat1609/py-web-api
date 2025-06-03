from typing import Optional
from pydantic import BaseModel, EmailStr


class UserInDB(BaseModel):
    username: str
    age: int
    email: EmailStr
    hashed_password: str

    class Config:
        orm_mode = True
