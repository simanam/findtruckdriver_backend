"""
Follow-Up Question Engine
Determines what question to ask based on status transition context
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from app.models.follow_up import (
    FollowUpQuestion,
    StatusContext,
    build_detention_question,
    build_parking_safety_question,
    build_parking_vibe_question,
    build_ready_to_roll_question,
    build_parking_spot_question,
    build_facility_flow_question,
    build_drive_safe_message
)
from app.utils.location import calculate_distance
import logging

logger = logging.getLogger(__name__)


class FollowUpEngine:
    """
    Contextual intelligence engine for follow-up questions.
    Implements the decision tree from status-follow-up-question.md
    """

    @staticmethod
    def calculate_context(
        prev_status: Optional[str],
        prev_latitude: Optional[float],
        prev_longitude: Optional[float],
        prev_updated_at: Optional[datetime],
        new_latitude: float,
        new_longitude: float
    ) -> StatusContext:
        """Calculate context about the status transition"""

        if not prev_status or prev_latitude is None or prev_updated_at is None:
            return StatusContext()

        # Calculate time since last update
        time_since = datetime.utcnow() - prev_updated_at.replace(tzinfo=None)
        time_since_seconds = int(time_since.total_seconds())
        time_since_hours = time_since_seconds / 3600

        # Calculate distance moved
        distance_miles = calculate_distance(
            prev_latitude, prev_longitude,
            new_latitude, new_longitude
        )

        # Determine location relationship
        is_same_location = distance_miles < 1.0
        is_nearby = distance_miles < 10.0

        return StatusContext(
            prev_status=prev_status,
            prev_latitude=prev_latitude,
            prev_longitude=prev_longitude,
            prev_updated_at=prev_updated_at,
            time_since_seconds=time_since_seconds,
            distance_miles=distance_miles,
            time_since_hours=time_since_hours,
            is_same_location=is_same_location,
            is_nearby=is_nearby
        )

    @staticmethod
    def get_follow_up_question(
        new_status: str,
        context: StatusContext,
        facility_name: Optional[str] = None
    ) -> Optional[FollowUpQuestion]:
        """
        Determine the right follow-up question based on context.
        Returns None if no question is appropriate.

        Phase 1 MVP: Focus on two high-value transitions:
        1. WAITING → ROLLING (detention tracking)
        2. PARKED → ROLLING (parking safety/vibe)
        """

        prev_status = context.prev_status

        # CASE 0: First time user or no previous context
        if not prev_status:
            logger.info(f"No previous status - skipping follow-up")
            return None

        # CASE 1: Returning after long absence (> 24 hours)
        if context.time_since_hours and context.time_since_hours > 24:
            logger.info(f"Long absence ({context.time_since_hours:.1f} hours) - skipping follow-up")
            return None

        # CASE 2: Status didn't change (just a check-in)
        if new_status == prev_status:
            logger.info(f"Same status - skipping follow-up")
            return None

        # CASE 3: Status changed - route to transition handler
        return FollowUpEngine._handle_transition(
            prev_status=prev_status,
            new_status=new_status,
            context=context,
            facility_name=facility_name
        )

    @staticmethod
    def _handle_transition(
        prev_status: str,
        new_status: str,
        context: StatusContext,
        facility_name: Optional[str]
    ) -> Optional[FollowUpQuestion]:
        """
        Handle specific status transitions.

        NEW PHILOSOPHY: Ask on ENTRY (PARKED, WAITING) when phone is in hand
        Only minimal questions on ROLLING (driver is about to drive)
        """

        transition = f"{prev_status}→{new_status}"
        logger.info(f"Transition: {transition}, time: {context.time_since_hours:.1f}h, distance: {context.distance_miles:.1f}mi")

        # ========================================
        # ASK ON ENTRY: Phone is in hand, has time
        # ========================================

        # → PARKED: Ask about spot immediately
        if new_status == "parked":
            logger.info(f"Entering PARKED - asking about spot")
            return build_parking_spot_question(facility_name)

        # → WAITING: Ask about facility flow immediately
        elif new_status == "waiting":
            logger.info(f"Entering WAITING - asking about facility flow")
            return build_facility_flow_question(facility_name)

        # ========================================
        # MINIMAL ON ROLLING: Don't distract driver
        # ========================================

        # → ROLLING from PARKED: Just encouragement
        elif prev_status == "parked" and new_status == "rolling":
            logger.info(f"PARKED → ROLLING: Drive safe message")
            return build_drive_safe_message()

        # → ROLLING from WAITING: Check detention time
        elif prev_status == "waiting" and new_status == "rolling":
            return FollowUpEngine._waiting_to_rolling(context, facility_name)

        # → ROLLING from anywhere else: Just encouragement
        elif new_status == "rolling":
            logger.info(f"{prev_status} → ROLLING: Drive safe message")
            return build_drive_safe_message()

        # ========================================
        # Other transitions
        # ========================================
        else:
            logger.info(f"Transition {transition} - no follow-up question")
            return None

    @staticmethod
    def _waiting_to_rolling(
        context: StatusContext,
        facility_name: Optional[str]
    ) -> Optional[FollowUpQuestion]:
        """
        WAITING → ROLLING transition
        Goal: Capture detention time and payment status

        This is THE GOLD - actual detention data from real drivers
        """

        wait_seconds = context.time_since_seconds or 0
        still_at_facility = context.is_same_location

        # CASE A: They're far from facility - updated late
        if context.distance_miles and context.distance_miles > 10:
            # They forgot to update, now 50 miles away
            # Don't ask about detention - moment has passed
            # We can still LOG the approximate wait time silently
            logger.info(f"Far from facility ({context.distance_miles:.1f}mi) - skipping detention question")
            return None

        # CASE B: Still at facility (< 1 mile) - ask based on wait time
        if still_at_facility:
            return build_detention_question(wait_seconds, facility_name)

        # CASE C: Nearby but not at facility (1-10 miles)
        # They might have driven to truck stop after getting loaded
        elif context.is_nearby:
            # Estimate drive time and subtract from wait
            estimated_drive_mins = context.distance_miles * 2  # Rough estimate: 30mph avg
            estimated_drive_seconds = int(estimated_drive_mins * 60)
            estimated_wait_seconds = max(0, wait_seconds - estimated_drive_seconds)

            if estimated_wait_seconds > 3600:  # More than 1 hour
                return build_detention_question(estimated_wait_seconds, facility_name)
            else:
                # Short wait, no need to ask
                return None

        # CASE D: Default - no question
        return None

    @staticmethod
    def _parked_to_rolling(
        context: StatusContext
    ) -> Optional[FollowUpQuestion]:
        """
        PARKED → ROLLING transition
        Goal: Capture parking safety/vibe and driver readiness

        Ask on EXIT, not entry - they now know if spot was safe
        """

        parked_hours = context.time_since_hours or 0
        same_spot = context.is_same_location

        # CASE A: Normal overnight rest (6-14 hours, same spot)
        if 6 <= parked_hours < 14 and same_spot:
            # They slept here - ask about the spot vibe
            return build_parking_vibe_question()

        # CASE B: Short rest (< 6 hours)
        elif parked_hours < 6 and same_spot:
            # Quick break - just acknowledge
            logger.info(f"Short rest ({parked_hours:.1f}h) - no question")
            return None

        # CASE C: Long rest (14+ hours) - maybe took 34-hour reset
        elif parked_hours >= 14 and same_spot:
            # Long rest - ask about readiness
            return build_ready_to_roll_question()

        # CASE D: Different location - they moved without updating
        else:
            logger.info(f"Different location or unusual time - no question")
            return None


# ============================================================================
# Convenience function for use in endpoints
# ============================================================================

def determine_follow_up(
    prev_status: Optional[str],
    prev_latitude: Optional[float],
    prev_longitude: Optional[float],
    prev_updated_at: Optional[datetime],
    new_status: str,
    new_latitude: float,
    new_longitude: float,
    facility_name: Optional[str] = None
) -> Tuple[StatusContext, Optional[FollowUpQuestion]]:
    """
    Convenience function to calculate context and determine follow-up question.

    Returns:
        Tuple of (context, question)
        question will be None if no follow-up is appropriate
    """

    engine = FollowUpEngine()

    # Calculate context
    context = engine.calculate_context(
        prev_status=prev_status,
        prev_latitude=prev_latitude,
        prev_longitude=prev_longitude,
        prev_updated_at=prev_updated_at,
        new_latitude=new_latitude,
        new_longitude=new_longitude
    )

    # Determine question
    question = engine.get_follow_up_question(
        new_status=new_status,
        context=context,
        facility_name=facility_name
    )

    return context, question
