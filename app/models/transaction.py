from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionBase(BaseModel):
    title: str
    amount: float
    type: str  # income, expense, debt, investment
    date: datetime
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None


class TransactionOut(TransactionBase):
    id: str
    createdAt: datetime
    updatedAt: datetime
