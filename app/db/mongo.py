from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load .env early so MONGODB_URI is available regardless of import order
load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")

if not MONGO_URI:
    # Provide a clear error to help with configuration issues
    raise RuntimeError("MONGODB_URI is not set. Ensure your .env is loaded and contains MONGODB_URI.")

# Initialize the MongoDB client
client = AsyncIOMotorClient(MONGO_URI)

# Access the database
db = client["finance_app"]
