"""
User routes - User management and approval system
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.database import get_db
from app.models import (
    UserCreate, UserResponse, UserUpdate, UserStatus,
    AdminCreate, AdminResponse, StatsResponse
)
from app.services.auth_service import require_api_key, require_auth


router = APIRouter()


def to_dict(doc: dict) -> dict:
    """Convert MongoDB document to dict with string ID"""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=dict)
async def create_user(data: UserCreate):
    """Register new user (pending approval)"""
    db = get_db()
    
    # Check if user already exists
    existing = await db.users.find_one({"telegram_id": data.telegram_id})
    if existing:
        return to_dict(existing)
    
    doc = {
        **data.model_dump(),
        "status": UserStatus.pending.value,
        "requested_at": datetime.utcnow(),
        "approved_at": None
    }
    
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return to_dict(doc)


@router.get("/", response_model=List[dict])
async def list_users(
    status: Optional[str] = Query(None),
    _=Depends(require_auth)
):
    """List users, optionally filtered by status"""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    cursor = db.users.find(query).sort("requested_at", -1)
    users = [to_dict(doc) async for doc in cursor]
    
    return users


@router.get("/{telegram_id}", response_model=dict)
async def get_user(telegram_id: int):
    """Get user by Telegram ID"""
    db = get_db()
    
    user = await db.users.find_one({"telegram_id": telegram_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return to_dict(user)


@router.get("/{telegram_id}/check")
async def check_user_status(telegram_id: int):
    """Check if user is approved"""
    db = get_db()
    
    user = await db.users.find_one({"telegram_id": telegram_id})
    
    if not user:
        return {"exists": False, "approved": False}
    
    return {
        "exists": True,
        "approved": user["status"] == UserStatus.approved.value,
        "status": user["status"]
    }


@router.patch("/{telegram_id}", response_model=dict)
async def update_user_status(
    telegram_id: int,
    data: UserUpdate,
    _=Depends(require_auth)
):
    """Approve/reject user"""
    db = get_db()
    
    updates = {"status": data.status.value}
    
    if data.status == UserStatus.approved:
        updates["approved_at"] = datetime.utcnow()
    
    result = await db.users.find_one_and_update(
        {"telegram_id": telegram_id},
        {"$set": updates},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    return to_dict(result)


@router.delete("/{telegram_id}")
async def delete_user(telegram_id: int, _=Depends(require_auth)):
    """Delete user"""
    db = get_db()
    
    result = await db.users.delete_one({"telegram_id": telegram_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/admins/", response_model=dict)
async def create_admin(data: AdminCreate, _=Depends(require_auth)):
    """Add new admin"""
    db = get_db()
    
    # Check if already exists
    existing = await db.admins.find_one({"telegram_id": data.telegram_id})
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")
    
    doc = data.model_dump()
    result = await db.admins.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return to_dict(doc)


@router.get("/admins/", response_model=List[dict])
async def list_admins(_=Depends(require_auth)):
    """List all admins"""
    db = get_db()
    
    cursor = db.admins.find()
    admins = [to_dict(doc) async for doc in cursor]
    
    return admins


@router.get("/admins/check/{telegram_id}")
async def check_admin(telegram_id: int):
    """Check if user is admin"""
    db = get_db()
    
    admin = await db.admins.find_one({"telegram_id": telegram_id})
    
    return {"is_admin": admin is not None}


@router.delete("/admins/{telegram_id}")
async def delete_admin(telegram_id: int, _=Depends(require_auth)):
    """Remove admin"""
    db = get_db()
    
    result = await db.admins.delete_one({"telegram_id": telegram_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats/", response_model=StatsResponse)
async def get_stats(_=Depends(require_auth)):
    """Get platform statistics"""
    db = get_db()
    
    total_films = await db.media.count_documents({"type": "film"})
    total_series = await db.media.count_documents({"type": "series"})
    total_episodes = await db.episodes.count_documents({})
    total_users = await db.users.count_documents({})
    pending_users = await db.users.count_documents({"status": "pending"})
    total_admins = await db.admins.count_documents({})
    
    return {
        "total_films": total_films,
        "total_series": total_series,
        "total_episodes": total_episodes,
        "total_users": total_users,
        "pending_users": pending_users,
        "total_admins": total_admins
    }
