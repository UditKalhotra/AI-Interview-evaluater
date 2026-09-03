"""
MongoDB connection layer (Motor, async).

Module 1 scope: establish the connection and expose a way to fetch the
database handle + ping it for the /health endpoint. No collections are
read/written yet — that starts in Module 2.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "voice_interview_db")

# Module-level singletons, created on app startup (see main.py lifespan)
client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


def connect_to_mongo() -> None:
    """Create the Motor client. Called once on FastAPI startup."""
    global client, db
    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]


def close_mongo_connection() -> None:
    """Close the Motor client. Called once on FastAPI shutdown."""
    global client
    if client is not None:
        client.close()


def get_database() -> AsyncIOMotorDatabase:
    """Return the active database handle. Raises if called before startup."""
    if db is None:
        raise RuntimeError("Database not initialized — connect_to_mongo() has not run yet.")
    return db


async def ping_database() -> bool:
    """Ping MongoDB to confirm the connection is alive. Used by /health."""
    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False
