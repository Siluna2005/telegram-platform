"""
Database connection and management
MongoDB with proper connection handling
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# Database connection
client: Optional[AsyncIOMotorClient] = None
db = None


async def connect_db():
    """Connect to MongoDB"""
    global client, db
    
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_NAME", "telegram_media_platform")
    
    print(f"📦 Connecting to MongoDB: {db_name}")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Test connection
    try:
        await client.admin.command('ping')
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise
    
    # Create indexes for better performance
    await create_indexes()


async def close_db():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


async def create_indexes():
    """Create database indexes for performance"""
    
    # Media indexes
    await db.media.create_index("type")
    await db.media.create_index("title")
    await db.media.create_index([("title", "text")])  # Full-text search
    
    # Film indexes
    await db.films.create_index("media_id", unique=True)
    
    # Episode indexes
    await db.episodes.create_index([("media_id", 1), ("season_number", 1), ("episode_number", 1)], unique=True)
    await db.episodes.create_index("media_id")
    
    # User indexes
    await db.users.create_index("telegram_id", unique=True)
    await db.users.create_index("status")
    
    # Admin indexes
    await db.admins.create_index("telegram_id", unique=True)
    
    # Upload indexes
    await db.uploads.create_index("user_id")
    await db.upload_queue.create_index([("user_id", 1), ("timestamp", 1)])
    
    print("✅ Database indexes created")


async def seed_admin():
    """Create admin user from environment variable"""
    admin_id = os.getenv("ADMIN_TELEGRAM_ID")
    
    if not admin_id:
        print("⚠️  No ADMIN_TELEGRAM_ID found in .env")
        return
    
    try:
        admin_id = int(admin_id)
        
        # Check if admin already exists
        existing = await db.admins.find_one({"telegram_id": admin_id})
        
        if not existing:
            await db.admins.insert_one({
                "telegram_id": admin_id,
                "username": "Admin",
                "note": "System admin from .env"
            })
            print(f"✅ Admin created: {admin_id}")
        else:
            print(f"✅ Admin exists: {admin_id}")
            
    except Exception as e:
        print(f"❌ Failed to seed admin: {e}")


def get_db():
    """Dependency for route handlers"""
    return db
