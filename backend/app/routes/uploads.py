"""
Upload routes - Video upload queue management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import UploadCreate, UploadResponse
from app.services.auth_service import require_api_key


router = APIRouter()


def to_dict(doc: dict) -> dict:
    """Convert MongoDB document to dict with string ID"""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE UPLOAD (Legacy)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=dict)
async def save_upload(data: UploadCreate, _=Depends(require_api_key)):
    """Save single upload (keeps last upload only)"""
    db = get_db()
    
    doc = {
        **data.model_dump(),
        "timestamp": datetime.utcnow()
    }
    
    await db.uploads.replace_one(
        {"user_id": data.user_id},
        doc,
        upsert=True
    )
    
    return {"success": True, "user_id": data.user_id}


@router.get("/{user_id}", response_model=dict)
async def get_upload(user_id: int, _=Depends(require_api_key)):
    """Get last upload for user"""
    db = get_db()
    
    upload = await db.uploads.find_one({"user_id": user_id})
    
    if not upload:
        raise HTTPException(status_code=404, detail="No upload found")
    
    return to_dict(upload)


@router.delete("/{user_id}")
async def clear_upload(user_id: int, _=Depends(require_api_key)):
    """Clear user's upload"""
    db = get_db()
    
    result = await db.uploads.delete_one({"user_id": user_id})
    
    return {"deleted": result.deleted_count > 0}


# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD QUEUE (Bulk Season Linking)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{user_id}/queue", response_model=dict)
async def add_to_queue(user_id: int, data: UploadCreate, _=Depends(require_api_key)):
    """Add upload to queue"""
    db = get_db()
    
    doc = {
        **data.model_dump(),
        "timestamp": datetime.utcnow()
    }
    
    result = await db.upload_queue.insert_one(doc)
    
    return {"success": True, "id": str(result.inserted_id)}


@router.get("/{user_id}/queue", response_model=List[dict])
async def get_queue(user_id: int, _=Depends(require_api_key)):
    """Get user's upload queue"""
    db = get_db()
    
    cursor = db.upload_queue.find({"user_id": user_id}).sort("timestamp", 1)
    queue = [to_dict(doc) async for doc in cursor]
    
    return queue


@router.get("/{user_id}/queue/count")
async def get_queue_count(user_id: int, _=Depends(require_api_key)):
    """Get queue count"""
    db = get_db()
    
    count = await db.upload_queue.count_documents({"user_id": user_id})
    
    return {"count": count, "user_id": user_id}


@router.delete("/{user_id}/queue")
async def clear_queue(user_id: int, _=Depends(require_api_key)):
    """Clear user's queue"""
    db = get_db()
    
    result = await db.upload_queue.delete_many({"user_id": user_id})
    
    return {"deleted": result.deleted_count}


@router.delete("/{user_id}/queue/{file_id}")
async def remove_from_queue(user_id: int, file_id: str, _=Depends(require_api_key)):
    """Remove specific file from queue"""
    db = get_db()
    
    result = await db.upload_queue.delete_one({
        "user_id": user_id,
        "file_id": file_id
    })
    
    return {"deleted": result.deleted_count > 0}
