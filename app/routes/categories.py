from fastapi import APIRouter, HTTPException, status, Depends, Body, Path

from app.db.mongo import db
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict
from app.utils.helpers import fix_id
from app.routes.auth import get_current_user  # 👈 New import

router = APIRouter()
collection = db["categories"]


@router.get("/")
async def list_transactions(current_user: str = Depends(get_current_user)):
    cursor = collection.find()

    results = []
    async for doc in cursor:
        results.append(fix_id(doc))
    return results