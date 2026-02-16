"""
Media routes - Films, Series, Episodes
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.database import get_db
from app.models import (
    MediaCreate, MediaUpdate, MediaResponse,
    FilmLink, FilmResponse,
    EpisodeLink, EpisodeResponse
)
from app.services.tmdb_service import fetch_tmdb_metadata
from app.services.auth_service import require_api_key


router = APIRouter()


def to_dict(doc: dict) -> dict:
    """Convert MongoDB document to dict with string ID"""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIA CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=dict)
async def create_media(data: MediaCreate, _=Depends(require_api_key)):
    """Create new film or series with TMDB metadata"""
    db = get_db()
    
    doc = {
        **data.model_dump(),
        "created_at": datetime.utcnow(),
    }
    
    # Fetch TMDB metadata
    try:
        tmdb = await fetch_tmdb_metadata(data.title, data.type.value, data.year)
        if tmdb:
            doc.update(tmdb)
    except Exception as e:
        print(f"TMDB fetch failed: {e}")
    
    result = await db.media.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return to_dict(doc)


@router.get("/", response_model=List[dict])
async def list_media(type: Optional[str] = Query(None)):
    """List all media, optionally filtered by type"""
    db = get_db()
    
    query = {}
    if type:
        query["type"] = type
    
    cursor = db.media.find(query).sort("created_at", -1)
    media = [to_dict(doc) async for doc in cursor]
    
    return media


@router.get("/search", response_model=List[dict])
async def search_media(q: str = Query(..., min_length=1)):
    """Search media by title"""
    db = get_db()
    
    cursor = db.media.find({
        "$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"original_title": {"$regex": q, "$options": "i"}}
        ]
    })
    
    results = [to_dict(doc) async for doc in cursor]
    return results


@router.get("/{media_id}", response_model=dict)
async def get_media(media_id: str):
    """Get media by ID"""
    db = get_db()
    
    try:
        doc = await db.media.find_one({"_id": ObjectId(media_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid media ID")
    
    if not doc:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return to_dict(doc)


@router.patch("/{media_id}", response_model=dict)
async def update_media(media_id: str, data: MediaUpdate, _=Depends(require_api_key)):
    """Update media"""
    db = get_db()
    
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        result = await db.media.find_one_and_update(
            {"_id": ObjectId(media_id)},
            {"$set": updates},
            return_document=True
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid media ID")
    
    if not result:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return to_dict(result)


@router.delete("/{media_id}")
async def delete_media(media_id: str, _=Depends(require_api_key)):
    """Delete media and all associated episodes/films"""
    db = get_db()
    
    try:
        oid = ObjectId(media_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid media ID")
    
    # Delete media
    media_result = await db.media.delete_one({"_id": oid})
    
    if media_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Delete associated films/episodes
    await db.films.delete_many({"media_id": media_id})
    await db.episodes.delete_many({"media_id": media_id})
    
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════════════════
# FILM LINKING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/film/link", response_model=dict)
async def link_film(data: FilmLink, _=Depends(require_api_key)):
    """Link video to film"""
    db = get_db()
    
    # Verify media exists and is a film
    try:
        media = await db.media.find_one({"_id": ObjectId(data.film_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid film ID")
    
    if not media:
        raise HTTPException(status_code=404, detail="Film not found")
    
    if media["type"] != "film":
        raise HTTPException(status_code=400, detail="Media is not a film")
    
    doc = {
        "media_id": data.film_id,
        "file_id": data.file_id,
        "message_id": data.message_id,
        "storage_bot": data.storage_bot,
        "uploader_id": data.uploader_id,
        "linked_at": datetime.utcnow()
    }
    
    await db.films.replace_one({"media_id": data.film_id}, doc, upsert=True)
    
    return {"success": True, "film_id": data.film_id}


@router.get("/film/{film_id}", response_model=dict)
async def get_film(film_id: str):
    """Get film video info"""
    db = get_db()
    
    film = await db.films.find_one({"media_id": film_id})
    
    if not film:
        raise HTTPException(status_code=404, detail="Film not linked")
    
    return to_dict(film)


# ═══════════════════════════════════════════════════════════════════════════════
# EPISODE LINKING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/episode/link", response_model=dict)
async def link_episode(data: EpisodeLink, _=Depends(require_api_key)):
    """Link video to episode"""
    db = get_db()
    
    # Verify media exists and is a series
    try:
        media = await db.media.find_one({"_id": ObjectId(data.media_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid media ID")
    
    if not media:
        raise HTTPException(status_code=404, detail="Series not found")
    
    if media["type"] != "series":
        raise HTTPException(status_code=400, detail="Media is not a series")
    
    doc = {
        "media_id": data.media_id,
        "season_number": data.season_number,
        "episode_number": data.episode_number,
        "file_id": data.file_id,
        "message_id": data.message_id,
        "storage_bot": data.storage_bot,
        "uploader_id": data.uploader_id,
        "linked_at": datetime.utcnow()
    }
    
    await db.episodes.replace_one(
        {
            "media_id": data.media_id,
            "season_number": data.season_number,
            "episode_number": data.episode_number
        },
        doc,
        upsert=True
    )
    
    return {"success": True}


@router.get("/{media_id}/seasons", response_model=List[int])
async def get_seasons(media_id: str):
    """Get list of season numbers"""
    db = get_db()
    
    seasons = await db.episodes.distinct("season_number", {"media_id": media_id})
    return sorted(seasons)


@router.get("/{media_id}/season/{season}", response_model=List[dict])
async def get_episodes(media_id: str, season: int):
    """Get all episodes in a season"""
    db = get_db()
    
    cursor = db.episodes.find({
        "media_id": media_id,
        "season_number": season
    }).sort("episode_number", 1)
    
    episodes = [to_dict(doc) async for doc in cursor]
    return episodes


@router.get("/{media_id}/season/{season}/episode/{episode}", response_model=dict)
async def get_episode(media_id: str, season: int, episode: int):
    """Get specific episode"""
    db = get_db()
    
    ep = await db.episodes.find_one({
        "media_id": media_id,
        "season_number": season,
        "episode_number": episode
    })
    
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    return to_dict(ep)


@router.delete("/{media_id}/season/{season}/episode/{episode}")
async def delete_episode(media_id: str, season: int, episode: int, _=Depends(require_api_key)):
    """Delete episode"""
    db = get_db()
    
    result = await db.episodes.delete_one({
        "media_id": media_id,
        "season_number": season,
        "episode_number": episode
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════════════════
# BULK SEASON LINKING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/season/link-bulk", response_model=dict)
async def link_season_bulk(
    media_id: str,
    season_number: int,
    episode_count: int,
    uploader_id: int,
    _=Depends(require_api_key)
):
    """Link multiple episodes from upload queue"""
    db = get_db()
    
    # Get uploads from queue
    cursor = db.upload_queue.find({"user_id": uploader_id}).sort("timestamp", 1).limit(episode_count)
    uploads = [doc async for doc in cursor]
    
    if len(uploads) < episode_count:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough uploads. Found {len(uploads)}, need {episode_count}"
        )
    
    # Link each episode
    linked = []
    for i, upload in enumerate(uploads):
        episode_num = i + 1
        
        try:
            doc = {
                "media_id": media_id,
                "season_number": season_number,
                "episode_number": episode_num,
                "file_id": upload["file_id"],
                "message_id": upload.get("message_id"),
                "storage_bot": upload["bot_name"],
                "uploader_id": uploader_id,
                "linked_at": datetime.utcnow()
            }
            
            await db.episodes.replace_one(
                {
                    "media_id": media_id,
                    "season_number": season_number,
                    "episode_number": episode_num
                },
                doc,
                upsert=True
            )
            
            # Remove from queue
            await db.upload_queue.delete_one({"_id": upload["_id"]})
            
            linked.append({"episode": episode_num, "success": True})
        except Exception as e:
            linked.append({"episode": episode_num, "success": False, "error": str(e)})
    
    success_count = sum(1 for x in linked if x["success"])
    
    return {
        "media_id": media_id,
        "season": season_number,
        "total_episodes": episode_count,
        "linked_successfully": success_count,
        "details": linked
    }
