"""
Auth Service - API key and JWT authentication
"""

from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os


# Security
security = HTTPBearer()

# Secrets
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-jwt-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_password(password: str, hashed_password: str) -> bool:
    """Simple password verification (use bcrypt in production)"""
    return password == hashed_password


async def require_api_key(x_api_key: str = Header(None)):
    """Dependency for API key authentication"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency for JWT authentication"""
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid authentication")
