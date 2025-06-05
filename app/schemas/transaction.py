from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransactionBase(BaseModel):
    title: str
    amount: float
    type: str  # income | expense | debt | investment
    date: datetime
    notes: Optional[str] = None


class TransactionRequest(BaseModel):
    id: str
    user_id: str


class TransactionUpdate(BaseModel):
    title: Optional[str]
    amount: Optional[float]
    category: Optional[str]
    date: Optional[str]
    notes: Optional[str]
