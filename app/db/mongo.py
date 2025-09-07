from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGODB_URI")

# Initialize the MongoDB client
client = AsyncIOMotorClient(MONGO_URI)

# Access the database
db = client["finance_app"]
