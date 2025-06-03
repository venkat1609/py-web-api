from pydantic import BaseModel

class User(BaseModel):
    username: str
    age: int
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
