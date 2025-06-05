from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://admin:Venkat1995@cluster0.feoiggt.mongodb.net/?retryWrites=true&w=majority",
)

# Initialize the MongoDB client
client = AsyncIOMotorClient(MONGO_URI)

# Access the database
db = client["finance_app"]
