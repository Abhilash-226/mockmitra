import uvicorn
import asyncio
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
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
