import httpx
from datetime import datetime
from app.db.mongo import db

EXCHANGE_API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"  # or any API
collection = db["exchange_rates"]


async def fetch_and_store_rates():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(EXCHANGE_API_URL)
            data = response.json()

        # Prepare document
        document = {
            "base": "usd",
            "rates": data["usd"],
            "date": data["date"],
            "fetched_at": datetime.utcnow(),
        }

        await collection.replace_one({"base": "usd"}, document, upsert=True)
        print(f"[{datetime.utcnow()}] Exchange rates fetched and stored.")

    except Exception as e:
        print(f"Error fetching exchange rates: {e}")
