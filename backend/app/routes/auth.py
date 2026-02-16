"""
Auth routes - Dashboard authentication
"""

from fastapi import APIRouter, HTTPException
from app.models import LoginRequest, TokenResponse
from app.services.auth_service import create_access_token, verify_password
import os


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Login to dashboard"""
    
    # Simple username/password from environment
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    if data.username != admin_username or data.password != admin_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token({"sub": data.username})
    
    return {"access_token": access_token, "token_type": "bearer"}
