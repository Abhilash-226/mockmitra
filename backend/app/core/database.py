from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import certifi
import ssl

from app.core.config import settings

# MongoDB client instance
client: AsyncIOMotorClient = None


async def init_db():
    """Initialize MongoDB connection and Beanie ODM"""
    global client
    
    # Check if using MongoDB Atlas (contains mongodb.net or mongodb+srv)
    is_atlas = "mongodb.net" in settings.MONGODB_URL or "mongodb+srv" in settings.MONGODB_URL
    
    if is_atlas:
        # Use certifi for SSL certificates with proper TLS settings for Atlas
        # Note: If SSL fails, your IP may not be whitelisted in MongoDB Atlas
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            tlsCAFile=certifi.where(),
            tls=True,
            tlsAllowInvalidCertificates=True,  # Workaround for Python 3.13 SSL issues
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=20000,
            retryWrites=True,
            w='majority'
        )
    else:
        # Local MongoDB - no TLS needed
        client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    # Import all document models
    from app.models.user import User
    from app.models.question import Question
    from app.models.test import Test, TestAttempt, TestResponse
    
    # Initialize Beanie with all document models
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[User, Question, Test, TestAttempt, TestResponse]
    )


async def close_db():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
