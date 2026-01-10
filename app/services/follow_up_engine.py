"""
Follow-Up Question Engine
Determines what question to ask based on status transition context
"""

from typing import Optional, Tuple, List
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
    build_drive_safe_message,
    # First-time user questions
    build_first_time_parked_question,
    build_first_time_waiting_question,
    build_first_time_rolling_message,
    # Returning user questions
    build_returning_user_question,
    # Check-in questions
    build_checkin_parked_short,
    build_checkin_parked_long,
    build_checkin_waiting,
    build_checkin_rolling,
    # WAITING → PARKED transition questions
    build_calling_it_a_night_question,
    build_done_at_facility_question,
    # PARKED → WAITING transition questions
    build_time_to_work_question,
    # Weather questions
    build_weather_alert_question,
    build_weather_check_question,
    build_weather_stay_safe_message,
    build_weather_good_message
)
from app.utils.location import calculate_distance
from app.services.weather_api import (
    get_weather_alerts,
    should_warn_driver,
    get_most_severe_alert,
    get_alert_emoji,
    get_weather_summary
)
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
        facility_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Optional[FollowUpQuestion]:
        """
        Determine the right follow-up question based on context.
        Returns the PRIMARY question (NOT weather - weather is handled separately).

        Implements complete edge case decision tree:
        1. First-time user → Welcome message
        2. Returning user (24+ hours) → Welcome back message
        3. Check-in (same status) → Conditional re-ask or confirmation
        4. Status transition → Context-aware question

        Note: Weather is now checked separately via get_weather_info()
        """

        prev_status = context.prev_status

        # CASE 1: First time user (no previous status)
        if not prev_status:
            logger.info(f"First-time user - showing welcome message for {new_status}")
            return FollowUpEngine._first_time_flow(new_status, facility_name)

        # CASE 2: Returning user (24+ hours away)
        if context.time_since_hours and context.time_since_hours >= 24:
            days_away = int(context.time_since_hours / 24)
            logger.info(f"Returning user after {days_away} days - showing welcome back")
            return build_returning_user_question(new_status, days_away, facility_name)

        # CASE 3: Check-in (same status)
        if new_status == prev_status:
            logger.info(f"Check-in for {new_status} status")
            return FollowUpEngine._check_in_flow(new_status, context)

        # CASE 4: Status transition
        return FollowUpEngine._handle_transition(
            prev_status=prev_status,
            new_status=new_status,
            context=context,
            facility_name=facility_name
        )

    @staticmethod
    def _check_weather(
        new_status: str,
        latitude: float,
        longitude: float
    ) -> Optional[FollowUpQuestion]:
        """
        Check for severe weather and return appropriate question.

        Safety is top priority - weather alerts override other questions.
        """
        try:
            alerts = get_weather_alerts(latitude, longitude)

            if not alerts:
                return None

            # Check if we should warn the driver
            if not should_warn_driver(alerts, new_status):
                return None

            most_severe = get_most_severe_alert(alerts)
            if not most_severe:
                return None

            emoji = get_alert_emoji(most_severe.event)
            weather_summary = get_weather_summary(alerts)

            logger.info(
                f"Severe weather detected: {most_severe.event} "
                f"(severity: {most_severe.severity}, urgency: {most_severe.urgency})"
            )

            # Different questions based on driver status
            if new_status == "rolling":
                # Driver is driving - ask if they're safe
                return build_weather_alert_question(
                    most_severe.event,
                    most_severe.headline,
                    emoji
                )

            elif new_status == "waiting":
                # Driver is waiting - light check on conditions
                if weather_summary:
                    return build_weather_check_question(weather_summary)

            elif new_status == "parked":
                # Driver is parked - encourage staying safe
                if weather_summary:
                    return build_weather_stay_safe_message(weather_summary)

            return None

        except Exception as e:
            logger.error(f"Weather check failed: {e}", exc_info=True)
            return None

    @staticmethod
    def _first_time_flow(new_status: str, facility_name: Optional[str]) -> FollowUpQuestion:
        """
        Handle first-time user based on their initial status.
        Show welcoming message with appropriate question for their status.
        """
        if new_status == "parked":
            return build_first_time_parked_question()
        elif new_status == "waiting":
            return build_first_time_waiting_question(facility_name)
        else:  # rolling
            return build_first_time_rolling_message()

    @staticmethod
    def _check_in_flow(status: str, context: StatusContext) -> Optional[FollowUpQuestion]:
        """
        Handle check-in (same status) based on time in status.
        Short check-ins get quick acknowledgment, longer ones get re-asked.
        """
        time_in_status_hours = context.time_since_hours or 0

        if status == "parked":
            if time_in_status_hours < 2:
                # Short time - just acknowledge location update
                return build_checkin_parked_short()
            else:
                # Longer time - re-ask about spot quality (things change)
                return build_checkin_parked_long()

        elif status == "waiting":
            # Always re-ask - facility flow changes frequently
            return build_checkin_waiting()

        else:  # rolling
            # Just acknowledge - they're driving
            return build_checkin_rolling()

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

        # → PARKED: Context-based question
        if new_status == "parked":
            # WAITING → PARKED (special context-aware handling)
            if prev_status == "waiting":
                return FollowUpEngine._waiting_to_parked(context, facility_name)
            # ROLLING → PARKED (normal parking)
            else:
                logger.info(f"Entering PARKED - asking about spot")
                return build_parking_spot_question(facility_name)

        # → WAITING: Context-based question
        elif new_status == "waiting":
            # PARKED → WAITING (woke up, ready to work)
            if prev_status == "parked":
                logger.info(f"PARKED → WAITING - time to work")
                return build_time_to_work_question(facility_name)
            # ROLLING → WAITING (normal arrival)
            else:
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
    def _waiting_to_parked(
        context: StatusContext,
        facility_name: Optional[str]
    ) -> Optional[FollowUpQuestion]:
        """
        WAITING → PARKED transition
        Goal: Determine if driver is done for the day or still waiting

        Three scenarios:
        1. Same location (<0.5 mi) → "Calling it a night?" (might be status correction)
        2. Nearby truck stop (<15 mi, 2+ hr wait) → Ask about detention pay
        3. Anywhere else → Ask about parking spot
        """

        wait_seconds = context.time_since_seconds or 0
        distance = context.distance_miles or 0

        # CASE A: Same location - probably parking at facility overnight
        if distance < 0.5:
            logger.info(f"WAITING → PARKED same location - calling it a night?")
            return build_calling_it_a_night_question()

        # CASE B: Nearby (<15 miles) - drove to truck stop after load
        elif distance < 15:
            # Long wait (2+ hours) - ask about detention
            if wait_seconds >= 7200:  # 2 hours
                prev_facility = facility_name or "the facility"
                logger.info(f"WAITING → PARKED nearby after {wait_seconds}s wait - detention question")
                return build_done_at_facility_question(prev_facility, wait_seconds)
            # Short wait - just ask about parking spot
            else:
                logger.info(f"WAITING → PARKED nearby after short wait - ask about spot")
                return build_parking_spot_question(facility_name)

        # CASE C: Far away - forgot to update, just ask about current spot
        else:
            logger.info(f"WAITING → PARKED far away ({distance:.1f}mi) - ask about spot")
            return build_parking_spot_question(facility_name)

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
) -> Tuple[StatusContext, Optional[FollowUpQuestion], Optional[FollowUpQuestion]]:
    """
    Convenience function to calculate context and determine follow-up questions.

    NOW RETURNS TWO QUESTIONS:
    1. Primary follow-up question (detention, parking, facility flow, etc.)
    2. Weather information (good or bad conditions)

    Returns:
        Tuple of (context, primary_question, weather_question)
        Either question can be None if not appropriate
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

    # Get primary follow-up question (NOT weather)
    primary_question = engine.get_follow_up_question(
        new_status=new_status,
        context=context,
        facility_name=facility_name,
        latitude=None,  # Don't check weather here anymore
        longitude=None
    )

    # Get weather info separately (ALWAYS check)
    weather_question = get_weather_info(
        new_status=new_status,
        latitude=new_latitude,
        longitude=new_longitude
    )

    return context, primary_question, weather_question

def get_weather_info(
    new_status: str,
    latitude: float,
    longitude: float
) -> Optional[FollowUpQuestion]:
    """
    Get weather ALERTS for follow-up questions.

    ONLY returns a question if there's a severe weather alert that needs driver attention.
    Does NOT return anything for good weather - that's shown in the stats bar instead.

    Args:
        new_status: Driver's new status
        latitude: Current latitude
        longitude: Current longitude

    Returns:
        Weather alert question, or None if no alerts or not severe enough
    """
    try:
        alerts = get_weather_alerts(latitude, longitude)

        # No alerts - return None (good weather shown in stats bar)
        if not alerts:
            logger.info("Weather: No alerts - stats bar will show current conditions")
            return None

        most_severe = get_most_severe_alert(alerts)
        if not most_severe:
            return None

        emoji = get_alert_emoji(most_severe.event)
        weather_summary = get_weather_summary(alerts)

        logger.info(
            f"Weather alert: {most_severe.event} "
            f"(severity: {most_severe.severity}, urgency: {most_severe.urgency})"
        )

        # Only show alerts for Severe/Extreme weather
        if most_severe.severity in ["Severe", "Extreme"]:
            # Different questions based on driver status
            if new_status == "rolling":
                # CRITICAL: Driver is driving in severe weather
                return build_weather_alert_question(
                    most_severe.event,
                    most_severe.headline,
                    emoji
                )
            elif new_status == "waiting":
                # Ask about road conditions
                return build_weather_check_question(weather_summary)
            else:  # parked
                # Encourage staying safe
                return build_weather_stay_safe_message(weather_summary)

        # Moderate alerts - only warn rolling drivers
        elif most_severe.severity == "Moderate":
            if new_status == "rolling":
                return build_weather_check_question(weather_summary)

        # Not severe enough to warrant a follow-up question
        logger.info(f"Weather alert not severe enough for follow-up: {most_severe.severity}")
        return None

    except Exception as e:
        logger.error(f"Weather check failed: {e}", exc_info=True)
        return None
