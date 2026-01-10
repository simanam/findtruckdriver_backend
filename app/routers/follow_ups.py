"""
Follow-Up Questions Router
Endpoints for recording driver responses to follow-up questions
"""

from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client
from datetime import datetime
from app.database import get_db_admin
from app.models.follow_up import FollowUpResponse
from app.dependencies import get_current_driver
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/follow-ups", tags=["Follow-Up Questions"])


@router.post("/respond")
async def record_follow_up_response(
    response: FollowUpResponse,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Record driver's response to a follow-up question.

    This endpoint is called when a driver answers a follow-up question
    that was presented after a status update. The response is saved to
    the status_update record for analytics and facility metrics.

    Example:
    POST /api/v1/follow-ups/respond
    {
        "status_update_id": "uuid-here",
        "response_value": "paid",
        "response_text": null
    }
    """
    try:
        # Verify this status_update belongs to this driver
        status_update = db.from_("status_updates") \
            .select("*") \
            .eq("id", str(response.status_update_id)) \
            .eq("driver_id", driver["id"]) \
            .single() \
            .execute()

        if not status_update.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Status update not found or does not belong to you"
            )

        # Verify this status_update has a follow-up question
        if not status_update.data.get("follow_up_question_type"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This status update does not have a follow-up question"
            )

        # Verify response hasn't already been recorded
        if status_update.data.get("follow_up_answered_at"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Follow-up question has already been answered"
            )

        # Check for status correction ("Still waiting" on "Calling it a night?")
        needs_status_correction = (
            status_update.data.get("follow_up_question_type") == "calling_it_a_night" and
            response.response_value == "still_waiting"
        )

        # Update with response
        update_result = db.from_("status_updates").update({
            "follow_up_response": response.response_value,
            "follow_up_response_text": response.response_text,
            "follow_up_answered_at": datetime.utcnow().isoformat()
        }).eq("id", str(response.status_update_id)).execute()

        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record response"
            )

        logger.info(
            f"Driver {driver['id']} answered follow-up: " +
            f"{status_update.data['follow_up_question_type']} = {response.response_value}"
        )

        # Handle status correction
        if needs_status_correction:
            logger.info(f"Status correction: Driver {driver['id']} selected 'Still waiting' - correcting PARKED → WAITING")

            # Update driver status back to WAITING
            db.from_("drivers").update({
                "status": "waiting",
                "last_active": datetime.utcnow().isoformat()
            }).eq("id", driver["id"]).execute()

            # Create a new corrected status update
            db.from_("status_updates").insert({
                "driver_id": driver["id"],
                "status": "waiting",
                "prev_status": "parked",
                "latitude": status_update.data["latitude"],
                "longitude": status_update.data["longitude"],
                "facility_id": status_update.data.get("facility_id"),
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            return {
                "success": True,
                "message": "Status corrected to WAITING",
                "status_update_id": str(response.status_update_id),
                "status_corrected": True,
                "new_status": "waiting"
            }

        # TODO: Phase 2 - Update facility_metrics in background job
        # For now, we're just recording the response. Later, we'll aggregate
        # these responses into facility_metrics for public display.

        return {
            "success": True,
            "message": "Response recorded successfully",
            "status_update_id": str(response.status_update_id),
            "status_corrected": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record follow-up response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record response: {str(e)}"
        )


@router.get("/history")
async def get_my_follow_up_history(
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin),
    limit: int = 50
):
    """
    Get driver's follow-up question history.

    Returns all status updates that had follow-up questions,
    showing which questions were asked and how the driver responded.

    Useful for debugging and for drivers to review their own data.
    """
    try:
        # Get status updates with follow-up questions
        result = db.from_("status_updates") \
            .select("*") \
            .eq("driver_id", driver["id"]) \
            .not_.is_("follow_up_question_type", "null") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        history = []
        for record in result.data if result.data else []:
            history.append({
                "status_update_id": record["id"],
                "status": record["status"],
                "prev_status": record["prev_status"],
                "created_at": record["created_at"],
                "question_type": record["follow_up_question_type"],
                "question_text": record["follow_up_question_text"],
                "response_value": record.get("follow_up_response"),
                "answered_at": record.get("follow_up_answered_at"),
                "was_answered": record.get("follow_up_answered_at") is not None
            })

        return {
            "count": len(history),
            "history": history
        }

    except Exception as e:
        logger.error(f"Failed to get follow-up history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )
