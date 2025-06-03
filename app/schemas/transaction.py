from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransactionBase(BaseModel):
    title: str
    amount: float
    type: str  # income | expense | debt | investment
    date: datetime
    notes: Optional[str] = None
