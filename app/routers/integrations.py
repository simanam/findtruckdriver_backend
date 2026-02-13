"""
Integrations Router
Endpoints for Google Places search/confirm, FMCSA confirm, and role_details updates.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from supabase import Client
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
from app.database import get_db_admin
from app.models.integrations import (
    GooglePlacesSearchRequest,
    FMCSAConfirmRequest,
    GooglePlacesConfirmRequest,
    RoleDetailsUpdateRequest,
)
from app.services.google_places_api import search_places
from app.services.profile_completion import calculate_completion, check_badges
from app.config import settings
from app.dependencies import get_current_driver
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])

limiter = Limiter(key_func=get_remote_address)


def _get_profile(db: Client, driver_id: str) -> dict:
    """Fetch the professional profile for a driver, or raise 404."""
    response = db.from_("professional_profiles").select("*").eq(
        "driver_id", driver_id
    ).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found. Create one first."
        )
    return response.data[0]


def _parse_role_details(raw) -> dict:
    """Parse role_details from DB (may be string or dict)."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return raw if isinstance(raw, dict) else {}


def _save_role_details_and_badges(db: Client, driver_id: str, profile: dict, role_details: dict) -> dict:
    """Save role_details, recalculate badges, and return updated profile."""
    merged = {**profile, "role_details": role_details}

    existing_badges = profile.get("badges", [])
    if isinstance(existing_badges, str):
        existing_badges = json.loads(existing_badges)

    updated_badges = check_badges(merged, existing_badges)

    update_dict = {
        "role_details": json.dumps(role_details),
        "badges": json.dumps(updated_badges),
        "completion_percentage": calculate_completion(merged),
    }

    response = db.from_("professional_profiles").update(update_dict).eq(
        "driver_id", driver_id
    ).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

    return response.data[0]


@router.post("/google-places/search")
@limiter.limit("20/minute")
async def search_google_places(
    request: Request,
    body: GooglePlacesSearchRequest,
    driver: dict = Depends(get_current_driver),
):
    """
    Search Google Places for businesses (mechanic shops, etc.).
    Proxies the request to avoid exposing the API key to the browser.

    Rate limited: 20 requests per minute per IP.
    """
    if not settings.google_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google API key not configured. Please set GOOGLE_API_KEY in environment."
        )

    try:
        results = search_places(
            query=body.query,
            api_key=settings.google_api_key,
            location=body.location,
        )
        return {
            "results": [r.to_dict() for r in results],
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Google Places search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search Google Places"
        )


@router.post("/google-places/confirm")
@limiter.limit("10/minute")
async def confirm_google_place(
    request: Request,
    body: GooglePlacesConfirmRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin),
):
    """
    Confirm and save Google Places verification data to role_details.
    Awards the 'google_verified' badge.
    """
    try:
        profile = _get_profile(db, driver["id"])
        role_details = _parse_role_details(profile.get("role_details", {}))

        role_details["google_verified"] = True
        role_details["google_data"] = body.google_data
        role_details["google_verified_at"] = datetime.utcnow().isoformat()

        updated = _save_role_details_and_badges(db, driver["id"], profile, role_details)

        logger.info(f"Google Places verified for driver {driver['id']}")
        return {"success": True, "message": "Google Places verification saved", "profile": updated}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google Places confirm error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm Google Places data: {str(e)}"
        )


@router.post("/fmcsa/confirm")
@limiter.limit("10/minute")
async def confirm_fmcsa(
    request: Request,
    body: FMCSAConfirmRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin),
):
    """
    Confirm and save FMCSA verification data to role_details.
    Awards the 'fmcsa_verified' badge.
    """
    try:
        profile = _get_profile(db, driver["id"])
        role_details = _parse_role_details(profile.get("role_details", {}))

        role_details["fmcsa_verified"] = True
        role_details["fmcsa_data"] = body.fmcsa_data
        role_details["fmcsa_verified_at"] = datetime.utcnow().isoformat()

        updated = _save_role_details_and_badges(db, driver["id"], profile, role_details)

        logger.info(f"FMCSA verified for driver {driver['id']}")
        return {"success": True, "message": "FMCSA verification saved", "profile": updated}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FMCSA confirm error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm FMCSA data: {str(e)}"
        )


@router.patch("/role-details")
@limiter.limit("20/minute")
async def update_role_details(
    request: Request,
    body: RoleDetailsUpdateRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin),
):
    """
    Update role-specific details (mechanic specialties, dispatcher fleet size, etc.).
    Merges the provided fields into existing role_details.
    """
    try:
        profile = _get_profile(db, driver["id"])
        existing_details = _parse_role_details(profile.get("role_details", {}))

        # Merge new fields into existing (shallow merge)
        merged_details = {**existing_details, **body.role_details}

        updated = _save_role_details_and_badges(db, driver["id"], profile, merged_details)

        logger.info(f"Role details updated for driver {driver['id']} - keys: {list(body.role_details.keys())}")
        return {"success": True, "message": "Role details updated", "profile": updated}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role details update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role details: {str(e)}"
        )
