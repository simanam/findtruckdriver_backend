"""
Professional Profile Router
Endpoints for professional profile CRUD, public views, and open-to-work listings
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, UploadFile, File
from supabase import Client
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db_admin
from app.models.professional_profile import (
    ProfessionalProfileCreate,
    ProfessionalProfileUpdate,
    ProfessionalProfileResponse,
    ProfessionalProfilePublic,
    OpenToWorkListItem,
)
from app.services.miles_calculator import calculate_estimated_miles, format_miles_display
from app.services.profile_completion import calculate_completion, check_badges
from app.services.fmcsa_api import search_by_dot, search_by_name
from app.config import settings
from app.dependencies import get_current_user, get_current_driver
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/professional", tags=["Professional Profile"])

# Rate limiter for profile endpoints
limiter = Limiter(key_func=get_remote_address)


def _build_full_response(profile: dict) -> dict:
    """
    Build a full ProfessionalProfileResponse dict from a raw DB row,
    adding the computed estimated_miles_display field.
    """
    result = dict(profile)
    miles = result.get("estimated_miles")
    result["estimated_miles_display"] = format_miles_display(miles) if miles else None
    # Ensure badges is a list (may come back as JSON string from DB)
    badges = result.get("badges", [])
    if isinstance(badges, str):
        result["badges"] = json.loads(badges)
    # Ensure work_history is a list
    wh = result.get("work_history", [])
    if isinstance(wh, str):
        result["work_history"] = json.loads(wh)
    return result


def _apply_privacy_filter(profile: dict) -> dict:
    """
    Apply privacy flags to a profile dict, removing hidden fields.
    Returns a new dict suitable for ProfessionalProfilePublic.
    """
    result = {
        "id": profile.get("id"),
        "driver_id": profile.get("driver_id"),
        "bio": profile.get("bio"),
        "open_to_work": profile.get("open_to_work", False),
        "badges": json.loads(profile["badges"]) if isinstance(profile.get("badges"), str) else profile.get("badges", []),
        "specialties": profile.get("specialties"),
        "looking_for": profile.get("looking_for"),
        "preferred_haul": profile.get("preferred_haul"),
        "completion_percentage": profile.get("completion_percentage", 0),
    }

    # Conditionally include fields based on show_* flags
    if profile.get("show_experience", True):
        result["years_experience"] = profile.get("years_experience")
        result["haul_type"] = profile.get("haul_type")
        result["estimated_miles"] = profile.get("estimated_miles")
        miles = profile.get("estimated_miles")
        result["estimated_miles_display"] = format_miles_display(miles) if miles else None

    if profile.get("show_equipment", True):
        result["equipment_type"] = profile.get("equipment_type")

    if profile.get("show_company", True):
        result["company_name"] = profile.get("company_name")

    if profile.get("show_cdl", True):
        result["cdl_class"] = profile.get("cdl_class")
        result["cdl_state"] = profile.get("cdl_state")
        result["endorsements"] = profile.get("endorsements")

    return result


@router.post("/profile", response_model=ProfessionalProfileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_professional_profile(
    request: Request,
    profile_data: ProfessionalProfileCreate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Create a professional profile for the current driver.
    Each driver can only have one professional profile.

    Rate limited: 10 requests per minute per IP.
    """
    try:
        # Check if professional profile already exists
        existing = db.from_("professional_profiles").select("id").eq(
            "driver_id", driver["id"]
        ).execute()

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Professional profile already exists. Use PATCH /profile/me to update."
            )

        # Build profile dict
        profile_dict = profile_data.model_dump(exclude_unset=True)
        profile_dict["driver_id"] = driver["id"]

        # Calculate estimated miles if we have the data
        years = profile_dict.get("years_experience")
        haul_type = profile_dict.get("haul_type")
        if years is not None:
            profile_dict["estimated_miles"] = calculate_estimated_miles(years, haul_type)

        # Serialize work_history for JSONB storage
        if "work_history" in profile_dict and profile_dict["work_history"] is not None:
            profile_dict["work_history"] = json.dumps([
                entry.model_dump() if hasattr(entry, 'model_dump') else entry
                for entry in profile_dict["work_history"]
            ])

        # Calculate completion percentage
        profile_dict["completion_percentage"] = calculate_completion(profile_dict)

        # Check and award badges
        profile_dict["badges"] = json.dumps(check_badges(profile_dict))

        # Insert profile
        response = db.from_("professional_profiles").insert(profile_dict).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create professional profile"
            )

        logger.info(f"Professional profile created for driver {driver['id']}")

        return _build_full_response(response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create professional profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create professional profile: {str(e)}"
        )


@router.get("/profile/me", response_model=ProfessionalProfileResponse)
async def get_my_professional_profile(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Get the current driver's own professional profile.
    Returns the full profile with all fields (no privacy filtering).
    """
    try:
        response = db.from_("professional_profiles").select("*").eq(
            "driver_id", driver["id"]
        ).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professional profile not found. Create one with POST /professional/profile."
            )

        return _build_full_response(response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch professional profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch professional profile"
        )


@router.patch("/profile/me", response_model=ProfessionalProfileResponse)
@limiter.limit("20/minute")
async def update_my_professional_profile(
    request: Request,
    updates: ProfessionalProfileUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Update the current driver's professional profile.
    Only updates the provided fields (PATCH semantics).
    Automatically recalculates estimated miles, completion percentage, and badges.

    Rate limited: 20 requests per minute per IP.
    """
    try:
        # Get existing profile
        existing = db.from_("professional_profiles").select("*").eq(
            "driver_id", driver["id"]
        ).execute()

        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professional profile not found. Create one with POST /professional/profile."
            )

        current_profile = existing.data[0]

        # Build update dict from provided fields only
        update_dict = updates.model_dump(exclude_unset=True)

        if not update_dict:
            return _build_full_response(current_profile)

        # Merge current profile with updates for recalculations
        merged_profile = {**current_profile, **update_dict}

        # Recalculate estimated miles if relevant fields changed
        if "years_experience" in update_dict or "haul_type" in update_dict:
            years = merged_profile.get("years_experience")
            haul_type = merged_profile.get("haul_type")
            if years is not None:
                update_dict["estimated_miles"] = calculate_estimated_miles(years, haul_type)
                merged_profile["estimated_miles"] = update_dict["estimated_miles"]
            else:
                update_dict["estimated_miles"] = None
                merged_profile["estimated_miles"] = None

        # Serialize work_history for JSONB storage
        if "work_history" in update_dict and update_dict["work_history"] is not None:
            update_dict["work_history"] = json.dumps([
                entry.model_dump() if hasattr(entry, 'model_dump') else entry
                for entry in update_dict["work_history"]
            ])

        # Recalculate completion percentage
        update_dict["completion_percentage"] = calculate_completion(merged_profile)

        # Check and award badges
        existing_badges = current_profile.get("badges", [])
        if isinstance(existing_badges, str):
            existing_badges = json.loads(existing_badges)
        updated_badges = check_badges(merged_profile, existing_badges)
        update_dict["badges"] = json.dumps(updated_badges)

        # Update profile
        response = db.from_("professional_profiles").update(update_dict).eq(
            "driver_id", driver["id"]
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update professional profile"
            )

        logger.info(f"Professional profile updated for driver {driver['id']} - {list(update_dict.keys())}")

        return _build_full_response(response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update professional profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update professional profile: {str(e)}"
        )


@router.get("/profile/{driver_id}", response_model=ProfessionalProfilePublic)
async def get_public_professional_profile(
    driver_id: UUID,
    db: Client = Depends(get_db_admin)
):
    """
    Get a driver's public professional profile.
    Returns privacy-filtered data based on the profile's show_* flags.
    Returns 404 if profile doesn't exist or is not public.
    """
    try:
        response = db.from_("professional_profiles").select("*").eq(
            "driver_id", str(driver_id)
        ).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professional profile not found"
            )

        profile = response.data[0]

        # Check if profile is public
        if not profile.get("is_public", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professional profile not found"
            )

        return _apply_privacy_filter(profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch public professional profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch professional profile"
        )


@router.get("/profiles/open-to-work", response_model=List[OpenToWorkListItem])
async def list_open_to_work_profiles(
    limit: int = 20,
    offset: int = 0,
    haul_type: Optional[str] = None,
    cdl_class: Optional[str] = None,
    db: Client = Depends(get_db_admin)
):
    """
    List drivers who are open to work opportunities.
    Only returns public profiles with open_to_work=true.
    Supports pagination with limit/offset and optional filters.
    """
    try:
        # Clamp limit
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        # Build query
        query = db.from_("professional_profiles").select(
            "*, drivers!inner(id, handle, avatar_id, profile_photo_url)"
        ).eq("open_to_work", True).eq("is_public", True)

        # Apply optional filters
        if haul_type:
            query = query.eq("haul_type", haul_type)
        if cdl_class:
            query = query.eq("cdl_class", cdl_class)

        # Apply pagination and ordering
        query = query.order("updated_at", desc=True).range(offset, offset + limit - 1)

        response = query.execute()

        if not response.data:
            return []

        # Build response list
        results = []
        for row in response.data:
            driver_info = row.get("drivers", {})
            miles = row.get("estimated_miles")
            results.append(OpenToWorkListItem(
                driver_id=row["driver_id"],
                handle=driver_info.get("handle"),
                avatar_id=driver_info.get("avatar_id"),
                profile_photo_url=driver_info.get("profile_photo_url"),
                years_experience=row.get("years_experience") if row.get("show_experience", True) else None,
                haul_type=row.get("haul_type") if row.get("show_experience", True) else None,
                equipment_type=row.get("equipment_type") if row.get("show_equipment", True) else None,
                estimated_miles=miles if row.get("show_experience", True) else None,
                estimated_miles_display=format_miles_display(miles) if miles and row.get("show_experience", True) else None,
                cdl_class=row.get("cdl_class") if row.get("show_cdl", True) else None,
                endorsements=row.get("endorsements") if row.get("show_cdl", True) else None,
                looking_for=row.get("looking_for"),
                preferred_haul=row.get("preferred_haul"),
                bio=row.get("bio"),
                badges=json.loads(row["badges"]) if isinstance(row.get("badges"), str) else row.get("badges", []),
                completion_percentage=row.get("completion_percentage", 0),
            ))

        return results

    except Exception as e:
        logger.error(f"Failed to list open-to-work profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list open-to-work profiles"
        )


@router.get("/fmcsa/search")
@limiter.limit("30/minute")
async def search_fmcsa_carriers(
    request: Request,
    q: str,
    type: str = "name",
    driver: dict = Depends(get_current_driver),
):
    """
    Search FMCSA database for carriers/companies.
    Supports search by DOT number or company name.

    Query params:
        q: Search query (DOT number or company name)
        type: "dot" or "name" (default: "name")

    Rate limited: 30 requests per minute per IP.
    """
    if not settings.fmcsa_web_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FMCSA API key not configured. Please set FMCSA_WEB_KEY in environment."
        )

    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )

    try:
        if type == "dot":
            carrier = search_by_dot(q.strip(), settings.fmcsa_web_key)
            results = [carrier.to_dict()] if carrier else []
        else:
            carriers = search_by_name(q.strip(), settings.fmcsa_web_key, limit=10)
            results = [c.to_dict() for c in carriers]

        return {"results": results, "count": len(results)}

    except Exception as e:
        logger.error(f"FMCSA search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search FMCSA database"
        )


@router.post("/profile/me/photo")
@limiter.limit("5/minute")
async def upload_profile_photo(
    request: Request,
    file: UploadFile = File(...),
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Upload a profile photo to Supabase Storage.
    Supports JPEG and PNG. Max size: 5MB.
    Updates the driver's profile_photo_url after successful upload.

    Rate limited: 5 uploads per minute per IP.
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{file.content_type}'. Allowed: {', '.join(allowed_types)}"
            )

        # Read file content
        content = await file.read()

        # Validate file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size is 5MB."
            )

        # Determine file extension
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }
        ext = ext_map.get(file.content_type, "jpg")

        # Build storage path: profile-photos/{driver_id}/photo.{ext}
        driver_id = driver["id"]
        file_path = f"profile-photos/{driver_id}/photo.{ext}"

        # Upload to Supabase Storage
        # Remove existing file first (ignore errors if not found)
        try:
            db.storage.from_("avatars").remove([file_path])
        except Exception:
            pass  # File may not exist yet

        upload_response = db.storage.from_("avatars").upload(
            file_path,
            content,
            {"content-type": file.content_type}
        )

        # Get public URL
        public_url = db.storage.from_("avatars").get_public_url(file_path)

        # Update driver's profile_photo_url
        db.from_("drivers").update({
            "profile_photo_url": public_url
        }).eq("id", driver_id).execute()

        logger.info(f"Profile photo uploaded for driver {driver_id}")

        return {
            "success": True,
            "photo_url": public_url,
            "message": "Profile photo uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload profile photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile photo: {str(e)}"
        )
