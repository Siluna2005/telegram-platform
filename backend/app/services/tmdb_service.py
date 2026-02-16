"""
TMDB Service - Fetch movie/series metadata
"""

import os
import httpx
from typing import Optional


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


async def fetch_tmdb_metadata(title: str, media_type: str, year: Optional[int] = None) -> Optional[dict]:
    """
    Fetch metadata from TMDB
    Returns dict with metadata or None if not found
    """
    
    if not TMDB_API_KEY:
        print("⚠️  TMDB_API_KEY not set, skipping metadata fetch")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Search for title
            search_url = f"{TMDB_BASE_URL}/search/{'movie' if media_type == 'film' else 'tv'}"
            params = {
                "api_key": TMDB_API_KEY,
                "query": title
            }
            
            if year:
                params["year" if media_type == "film" else "first_air_date_year"] = year
            
            response = await client.get(search_url, params=params)
            data = response.json()
            
            if not data.get("results"):
                print(f"No TMDB results for: {title}")
                return None
            
            # Get first result
            result = data["results"][0]
            tmdb_id = result["id"]
            
            # Get detailed info
            detail_url = f"{TMDB_BASE_URL}/{'movie' if media_type == 'film' else 'tv'}/{tmdb_id}"
            params = {
                "api_key": TMDB_API_KEY,
                "append_to_response": "credits"
            }
            
            response = await client.get(detail_url, params=params)
            details = response.json()
            
            # Extract metadata
            metadata = {
                "tmdb_id": tmdb_id,
                "overview": details.get("overview"),
                "description": details.get("overview"),
                "poster_url": f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else None,
                "backdrop_url": f"https://image.tmdb.org/t/p/original{details['backdrop_path']}" if details.get("backdrop_path") else None,
                "imdb_rating": details.get("vote_average"),
                "vote_count": details.get("vote_count"),
                "genres": [g["name"] for g in details.get("genres", [])],
                "genre": details["genres"][0]["name"] if details.get("genres") else None,
                "tagline": details.get("tagline"),
                "original_title": details.get("original_title") or details.get("original_name"),
            }
            
            # Type-specific fields
            if media_type == "film":
                metadata["year"] = int(details["release_date"][:4]) if details.get("release_date") else None
                metadata["runtime"] = f"{details.get('runtime')} min" if details.get("runtime") else None
            else:
                metadata["year"] = int(details["first_air_date"][:4]) if details.get("first_air_date") else None
                metadata["seasons_count"] = details.get("number_of_seasons")
                metadata["episodes_count"] = details.get("number_of_episodes")
            
            # Cast
            if details.get("credits", {}).get("cast"):
                metadata["cast"] = [
                    {
                        "name": actor["name"],
                        "character": actor.get("character"),
                        "profile_path": actor.get("profile_path")
                    }
                    for actor in details["credits"]["cast"][:10]
                ]
            
            # Directors
            if details.get("credits", {}).get("crew"):
                directors = [
                    person["name"]
                    for person in details["credits"]["crew"]
                    if person.get("job") == "Director"
                ]
                metadata["directors"] = directors
            
            print(f"✅ TMDB metadata fetched for: {title}")
            return metadata
            
    except Exception as e:
        print(f"❌ TMDB fetch error: {e}")
        return None
