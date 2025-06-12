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
    type_name: str  # income, expense, debt, investment
    category_id: str  # foreign key reference to categories._id
    category_name: str  # foreign key reference to categories._id
    date: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    notes: Optional[str] = None
    attachment: Optional[str] = None  # Attachment URL

    linkedSubscriptionId: Optional[str] = None  # Optional for linking to a subscription
    linkedLoanId: Optional[str] = None  # Optional for linking to a Loan

    person: Optional[str] = None  # Only filled for lend/borrow

    isGroup: bool = False  # True if the transaction is shared with a group
    groupId: Optional[str] = None
    participants: Optional[list[GroupBase]] = (
        None  # List of user IDs participating in the transaction
    )

    isRecurring: bool = False  # True if the transaction is recurring
    recurrenceType: Optional[str] = None  # e.g., daily, weekly, monthly
    endRecurrence: Optional[datetime] = None  # End date for recurring transactions
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
    type_name: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None
    attachment: Optional[str] = None
    linkedSubscriptionId: Optional[str] = None
    linkedLoanId: Optional[str] = None
    person: Optional[str] = None
    isGroup: Optional[bool] = None
    groupId: Optional[str] = None
    participants: Optional[list[GroupBase]] = None

    isRecurring: Optional[bool] = None
    recurrenceType: Optional[str] = None
    endRecurrence: Optional[datetime] = None

    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class TransactionResponse(TransactionBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class TransactionRequest(BaseModel):
    id: str
    userId: str
