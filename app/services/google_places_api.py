"""
Google Places API Service
Searches for businesses (mechanic shops, etc.) and retrieves place details.

API Docs: https://developers.google.com/maps/documentation/places/web-service
Endpoints:
  - POST https://places.googleapis.com/v1/places:searchText
  - GET  https://places.googleapis.com/v1/places/{place_id}
"""

import requests
import logging
from typing import Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(days=7)


@dataclass
class GooglePlaceData:
    """Normalized place data from Google Places API."""
    place_id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    types: Optional[List[str]] = None
    business_status: Optional[str] = None
    fetched_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# In-memory TTL cache
_cache: dict[str, tuple[object, datetime]] = {}


def _get_cached(key: str):
    if key in _cache:
        data, cached_at = _cache[key]
        if datetime.utcnow() - cached_at < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data):
    _cache[key] = (data, datetime.utcnow())


def _parse_address_components(components: list) -> dict:
    """Extract city, state, zip from Google address components."""
    result = {"city": None, "state": None, "zip_code": None}
    for comp in components or []:
        types = comp.get("types", [])
        if "locality" in types:
            result["city"] = comp.get("longText") or comp.get("shortText")
        elif "administrative_area_level_1" in types:
            result["state"] = comp.get("shortText")
        elif "postal_code" in types:
            result["zip_code"] = comp.get("longText") or comp.get("shortText")
    return result


def _parse_place(place: dict) -> GooglePlaceData:
    """Parse a Google Places API response into our dataclass."""
    addr = _parse_address_components(place.get("addressComponents", []))
    location = place.get("location", {})

    return GooglePlaceData(
        place_id=place.get("id"),
        name=place.get("displayName", {}).get("text"),
        address=place.get("formattedAddress"),
        city=addr["city"],
        state=addr["state"],
        zip_code=addr["zip_code"],
        latitude=location.get("latitude"),
        longitude=location.get("longitude"),
        phone=place.get("internationalPhoneNumber"),
        website=place.get("websiteUri"),
        rating=place.get("rating"),
        review_count=place.get("userRatingCount"),
        types=place.get("types"),
        business_status=place.get("businessStatus"),
        fetched_at=datetime.utcnow().isoformat(),
    )


def search_places(query: str, api_key: str, location: Optional[str] = None, limit: int = 5) -> List[GooglePlaceData]:
    """
    Search for places using Google Places Text Search (New) API.

    Args:
        query: Search text (e.g. "truck mechanic shop Dallas TX")
        api_key: Google API key
        location: Optional location bias (e.g. "Dallas, TX")
        limit: Max results to return

    Returns:
        List of GooglePlaceData results
    """
    cache_key = f"search:{query.lower().strip()}:{location or ''}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.addressComponents,places.location,places.internationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.types,places.businessStatus",
        }

        body = {
            "textQuery": f"{query} {location}" if location else query,
            "maxResultCount": min(limit, 10),
        }

        response = requests.post(url, json=body, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"Google Places API returned {response.status_code}: {response.text[:200]}")
            return []

        data = response.json()
        places = data.get("places", [])

        results = [_parse_place(p) for p in places[:limit]]
        _set_cache(cache_key, results)
        return results

    except requests.Timeout:
        logger.warning("Google Places API timeout")
        return []
    except requests.RequestException as e:
        logger.error(f"Google Places API request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Google Places API error: {e}", exc_info=True)
        return []


def get_place_details(place_id: str, api_key: str) -> Optional[GooglePlaceData]:
    """
    Get detailed info for a specific place by ID.
    """
    cache_key = f"details:{place_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,addressComponents,location,internationalPhoneNumber,websiteUri,rating,userRatingCount,types,businessStatus",
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"Google Places Details API returned {response.status_code}")
            return None

        place = response.json()
        result = _parse_place(place)
        _set_cache(cache_key, result)
        return result

    except requests.Timeout:
        logger.warning(f"Google Places Details API timeout for {place_id}")
        return None
    except requests.RequestException as e:
        logger.error(f"Google Places Details API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Google Places Details API error: {e}", exc_info=True)
        return None
