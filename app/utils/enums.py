from enum import Enum

class TransactionStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"
    refunded = "refunded"
    queued = "queued"
    partially_paid = "partially_paid"
    overdue = "overdue"