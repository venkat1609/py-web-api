from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GroupBase(BaseModel):
    id: str
    name: str
    amount: float
    createdAt: datetime
    updatedAt: datetime


class TransactionBase(BaseModel):
    userId: str  # foreign key reference to users._id
    title: str
    amount: float
    currency: str = Field(default="AED", description="Currency code, e.g., USD, EUR")
    type: str  # income, expense, debt, investment
    category: str  # foreign key reference to categories._id
    date: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    notes: Optional[str] = None
    attachment: Optional[str] = None  # Attachment URL

    linkedSubscriptionId: Optional[str] = None  # Optional for linking to a subscription
    linkedLoanId: Optional[str] = None  # Optional for linking to a Loan
    linkedUserId: Optional[str] = None  # Only filled for lend/borrow
    linkedGroupId: Optional[str] = None

    createdAt: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updatedAt: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):  # Optional so partial updates work
    userId: Optional[str] = None
    title: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None
    attachment: Optional[str] = None

    linkedSubscriptionId: Optional[str] = None
    linkedLoanId: Optional[str] = None
    linkedUserId: Optional[str] = None
    linkedGroupId: Optional[str] = None

    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class TransactionResponse(TransactionBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class TransactionRequest(BaseModel):
    id: str
    userId: str
