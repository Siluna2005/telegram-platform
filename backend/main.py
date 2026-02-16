"""
Telegram Media Platform - Backend API
FastAPI server for managing media, users, and bot interactions
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from app.routes import media, users, uploads, auth

# Import database
from app.database import connect_db, close_db, seed_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting Telegram Media Platform Backend...")
    await connect_db()
    await seed_admin()
    print("✅ Backend ready!")
    
    yield
    
    # Shutdown
    print("👋 Shutting down backend...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Telegram Media Platform API",
    description="Backend API for Telegram-based media streaming platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(media.router, prefix="/api/media", tags=["Media"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Telegram Media Platform",
        "version": "2.0.0"
    }


@app.get("/api/health")
async def health():
    """Detailed health check"""
    from app.database import db
    
    try:
        # Test MongoDB connection
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Set to True for development
    )
