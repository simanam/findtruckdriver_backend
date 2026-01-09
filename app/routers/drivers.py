"""
Driver Router
Endpoints for driver profile management
"""

from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client
from typing import List
from uuid import UUID
from app.database import get_db_admin
from app.models.driver import (
    DriverCreateRequest,
    DriverCreate,
    DriverUpdate,
    Driver,
    DriverPublic,
    StatusUpdate
)
from app.dependencies import get_current_user, get_current_driver
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drivers", tags=["Drivers"])


@router.post("", response_model=Driver, status_code=status.HTTP_201_CREATED)
async def create_driver_profile(
    driver_data: DriverCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db_admin)
):
    """
    Create driver profile for current user.
    This is the onboarding step after authentication.
    Frontend sends: { handle, avatar_id, status }
    Backend adds: user_id from authenticated user
    """
    try:
        # Check if driver profile already exists
        existing = db.from_("drivers").select("id").eq(
            "user_id", current_user.id
        ).execute()

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driver profile already exists"
            )

        # Check if handle is unique
        handle_check = db.from_("drivers").select("id").eq(
            "handle", driver_data.handle
        ).execute()

        if handle_check.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Handle '{driver_data.handle}' is already taken"
            )

        # Create driver profile - add user_id from authenticated user
        driver_dict = driver_data.model_dump()
        driver_dict["user_id"] = str(current_user.id)  # Convert to string for Supabase

        response = db.from_("drivers").insert(driver_dict).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create driver profile"
            )

        logger.info(f"Driver profile created for user {current_user.id}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create driver profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create driver profile: {str(e)}"
        )


@router.get("/me", response_model=Driver)
async def get_my_profile(
    driver: dict = Depends(get_current_driver)
):
    """
    Get current driver's full profile.
    """
    return driver


@router.put("/me", response_model=Driver)
async def update_my_profile(
    updates: DriverUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Update current driver's profile.
    """
    try:
        # If handle is being changed, check uniqueness
        if updates.handle and updates.handle != driver["handle"]:
            handle_check = db.from_("drivers").select("id").eq(
                "handle", updates.handle
            ).execute()

            if handle_check.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Handle '{updates.handle}' is already taken"
                )

        # Update profile
        update_dict = updates.model_dump(exclude_unset=True)

        response = db.from_("drivers").update(update_dict).eq(
            "id", driver["id"]
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

        logger.info(f"Driver profile updated: {driver['id']}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update driver profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/{driver_id}", response_model=DriverPublic)
async def get_driver_by_id(
    driver_id: UUID,
    db: Client = Depends(get_db_admin)
):
    """
    Get public driver profile by ID.
    Returns limited public information.
    """
    try:
        response = db.from_("drivers").select(
            "id,handle,first_name,status,created_at"
        ).eq("id", driver_id).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch driver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch driver"
        )


@router.get("/handle/{handle}", response_model=DriverPublic)
async def get_driver_by_handle(
    handle: str,
    db: Client = Depends(get_db_admin)
):
    """
    Get public driver profile by handle.
    Returns limited public information.
    """
    try:
        response = db.from_("drivers").select(
            "id,handle,first_name,status,created_at"
        ).eq("handle", handle).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver with handle '{handle}' not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch driver by handle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch driver"
        )


@router.post("/me/status", response_model=Driver)
async def update_my_status(
    status_update: StatusUpdate,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Update current driver's status.
    Valid statuses: rolling, waiting, parked.
    """
    try:
        # Update status
        response = db.from_("drivers").update({
            "status": status_update.status
        }).eq("id", driver["id"]).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update status"
            )

        logger.info(f"Driver {driver['id']} status updated to {status_update.status}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update driver status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update status"
        )
