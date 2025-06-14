from fastapi import APIRouter
from app.db.mongo import db
from app.utils.helpers import fix_id

router = APIRouter()
collection = db["exchange_rates"]

@router.get("/")
async def get_exchange_rates():
    cursor = collection.find().sort("date", -1)

    results = []
    async for doc in cursor:
        results.append(fix_id(doc))
    return results
