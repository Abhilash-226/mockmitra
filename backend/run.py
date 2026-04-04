import uvicorn
import asyncio
import os
from app.core.database import init_db


async def startup():
    """Initialize database on startup"""
    print("Initializing database...")
    await init_db()
    print("Database initialized!")


if __name__ == "__main__":
    # Initialize database
    asyncio.run(startup())
    
    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False
    )
