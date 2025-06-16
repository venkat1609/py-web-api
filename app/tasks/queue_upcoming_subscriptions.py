import httpx
from datetime import datetime, timedelta
from app.db.mongo import db

RECURRENCE_MAP = {"monthly": 30, "quarterly": 90, "yearly": 365}

collection = db["subscriptions"]


async def queue_upcoming_subscriptions():
    now = datetime.utcnow()
    cutoff = now + timedelta(days=30)

    subscriptions_cursor = collection.find(
        {
            "type": "expense",
            "isActive": True,
            "recurrenceType": {"$in": ["monthly", "quarterly", "yearly"]},
            "$or": [{"endDate": None}, {"endDate": {"$gt": now}}],
        }
    )

    async for sub in subscriptions_cursor:
        recurrence_days = RECURRENCE_MAP.get(sub.get("recurrenceType"))
        if not recurrence_days:
            continue

        start_date = sub["startDate"]
        if isinstance(start_date, dict) and "$date" in start_date:
            start_date = datetime.fromtimestamp(
                start_date["$date"]["$numberLong"] / 1000
            )

        days_since_start = (now - start_date).days
        cycles = days_since_start // recurrence_days
        next_due_date = start_date + timedelta(days=(cycles + 1) * recurrence_days)

        if now <= next_due_date <= cutoff:
            # Check for existing queued transaction
            existing = await db["transactions"].find_one(
                {
                    "userId": sub["userId"],
                    "linkedSubscriptionId": sub["_id"],
                    "date": next_due_date,
                    "status": "queued",
                }
            )

            if existing:
                print(f"Already queued: {sub['title']} for {next_due_date.date()}")
                continue  # Skip duplicate

            # Create new queued transaction
            transaction = {
                "userId": sub["userId"],
                "title": sub["title"],
                "description": sub.get("description", ""),
                "amount": sub["amount"],
                "type": sub["type"],
                "currency": sub["currency"],
                "category": sub["category"],
                "status": "queued",
                "notes": "",
                "date": next_due_date,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "linkedSubscriptionId": sub["_id"],
            }

            await db["transactions"].insert_one(transaction)
            print(f"Queued transaction for {sub['title']} on {next_due_date.date()}")
