from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db_name]

# Collections
skus_collection = db["skus"]
sales_history_collection = db["sales_history"]
reports_collection = db["reorder_reports"]  # cached agent reasoning, avoids re-calling LLM every request


async def ensure_indexes():
    await skus_collection.create_index("sku_id", unique=True)
    await sales_history_collection.create_index([("sku_id", 1), ("day", 1)])
    await reports_collection.create_index("sku_id")
