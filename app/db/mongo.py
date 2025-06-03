from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://admin:Venkat1995@cluster0.feoiggt.mongodb.net/?retryWrites=true&w=majority")
client = AsyncIOMotorClient(MONGO_URI)
db = client["finance_app"]
users_collection = db["users"]
