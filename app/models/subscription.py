from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SubscriptionBase(BaseModel):
    userId: str  # foreign key reference to users._id
    title: str
    description: str
    amount: float
    currency: str = Field(default="AED", description="Currency code, e.g., USD, EUR")
    type: str  # income, expense, debt, investment
    category: str  # foreign key reference to categories._id

    startDate: str

    endDate: Optional[str] = None

    notes: Optional[str] = None

    recurrenceType: str
    isActive: bool

    createdAt: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updatedAt: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):  # Optional so partial updates work
    title: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None

    type: Optional[str] = None

    category: Optional[str] = None

    startDate: Optional[str] = None
    endDate: Optional[str] = None

    notes: Optional[str] = None

    recurrenceType: str
    isActive: bool

    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class SubscriptionResponse(SubscriptionBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class SubscriptionRequest(BaseModel):
    id: str
    userId: str
