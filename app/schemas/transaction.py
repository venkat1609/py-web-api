from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransactionRequest(BaseModel):
    id: str
    user_id: str