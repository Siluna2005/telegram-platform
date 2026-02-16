"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class MediaType(str, Enum):
    film = "film"
    series = "series"


class UserStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class MediaCreate(BaseModel):
    title: str
    type: MediaType
    year: Optional[int] = None
    description: Optional[str] = None
    genre: Optional[str] = None


class MediaUpdate(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    genre: Optional[str] = None


class MediaResponse(BaseModel):
    id: str
    title: str
    type: MediaType
    year: Optional[int] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    genres: Optional[List[str]] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    imdb_rating: Optional[float] = None
    vote_count: Optional[int] = None
    runtime: Optional[str] = None
    tagline: Optional[str] = None
    original_title: Optional[str] = None
    cast: Optional[List[dict]] = None
    directors: Optional[List[str]] = None
    seasons_count: Optional[int] = None
    episodes_count: Optional[int] = None
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# FILM MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class FilmLink(BaseModel):
    film_id: str
    file_id: str
    message_id: Optional[int] = None
    storage_bot: str
    uploader_id: int


class FilmResponse(BaseModel):
    id: str
    media_id: str
    file_id: str
    message_id: Optional[int] = None
    storage_bot: str
    uploader_id: int


# ═══════════════════════════════════════════════════════════════════════════════
# EPISODE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class EpisodeLink(BaseModel):
    media_id: str
    season_number: int
    episode_number: int
    file_id: str
    message_id: Optional[int] = None
    storage_bot: str
    uploader_id: int


class EpisodeResponse(BaseModel):
    id: str
    media_id: str
    season_number: int
    episode_number: int
    file_id: str
    message_id: Optional[int] = None
    storage_bot: str
    uploader_id: int


# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class UploadCreate(BaseModel):
    user_id: int
    file_id: str
    bot_name: str
    message_id: Optional[int] = None


class UploadResponse(BaseModel):
    id: str
    user_id: int
    file_id: str
    message_id: Optional[int] = None
    bot_name: str
    timestamp: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# USER MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    status: UserStatus
    requested_at: datetime
    approved_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    status: UserStatus


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class AdminCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    note: Optional[str] = None


class AdminResponse(BaseModel):
    id: str
    telegram_id: int
    username: Optional[str] = None
    note: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ═══════════════════════════════════════════════════════════════════════════════
# STATS MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class StatsResponse(BaseModel):
    total_films: int
    total_series: int
    total_episodes: int
    total_users: int
    pending_users: int
    total_admins: int
