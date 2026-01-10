"""
Follow-Up Question Models
Pydantic models for contextual follow-up questions after status updates
"""

from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class FollowUpOption(BaseModel):
    """A single option in a follow-up question"""
    emoji: str = Field(..., description="Emoji icon for the option")
    label: str = Field(..., description="Display label")
    value: str = Field(..., description="Value to record")
    description: Optional[str] = Field(None, description="Optional longer description")


class FollowUpQuestion(BaseModel):
    """Follow-up question to ask after status update"""
    question_type: str = Field(..., description="Type of question (e.g., 'detention_payment', 'parking_safety')")
    text: str = Field(..., description="Question text to display")
    subtext: Optional[str] = Field(None, description="Optional smaller text below question")
    options: List[FollowUpOption] = Field(..., description="Answer options")
    skippable: bool = Field(True, description="Can user skip this question")
    auto_dismiss_seconds: Optional[int] = Field(None, description="Auto-dismiss after N seconds (for acknowledgments)")

    class Config:
        json_schema_extra = {
            "example": {
                "question_type": "detention_payment",
                "text": "2 hrs 34 min. Getting paid for that?",
                "subtext": "Sysco Houston",
                "options": [
                    {"emoji": "💰", "label": "Yep", "value": "paid"},
                    {"emoji": "😤", "label": "Nope", "value": "unpaid"},
                    {"emoji": "🤷", "label": "TBD", "value": "unknown"}
                ],
                "skippable": True,
                "auto_dismiss_seconds": None
            }
        }


class StatusContext(BaseModel):
    """Context about the status transition"""
    prev_status: Optional[str] = None
    prev_latitude: Optional[float] = None
    prev_longitude: Optional[float] = None
    prev_facility_name: Optional[str] = None
    prev_updated_at: Optional[datetime] = None

    time_since_seconds: Optional[int] = None
    distance_miles: Optional[float] = None

    # Convenience fields
    time_since_hours: Optional[float] = None
    is_same_location: Optional[bool] = None  # < 1 mile
    is_nearby: Optional[bool] = None  # < 10 miles


class FollowUpResponse(BaseModel):
    """Response to a follow-up question"""
    status_update_id: UUID = Field(..., description="ID of the status update")
    response_value: str = Field(..., description="The value selected (from options)")
    response_text: Optional[str] = Field(None, description="Optional free-text response")


class StatusUpdateWithFollowUp(BaseModel):
    """Status update response with optional follow-up question and weather info"""
    status_update_id: UUID
    status: str
    prev_status: Optional[str] = None
    context: Optional[StatusContext] = None
    follow_up_question: Optional[FollowUpQuestion] = None
    weather_info: Optional[FollowUpQuestion] = Field(None, description="Weather information (good or bad)")
    message: str = Field(..., description="Success message")


# ============================================================================
# Question Builder Helpers
# ============================================================================

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds} sec"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    remaining_mins = minutes % 60

    if remaining_mins == 0:
        return f"{hours} hr" if hours == 1 else f"{hours} hrs"
    else:
        return f"{hours} hr {remaining_mins} min"


def build_detention_question(
    wait_seconds: int,
    facility_name: Optional[str]
) -> FollowUpQuestion:
    """Build detention payment question based on wait time"""

    wait_hours = wait_seconds / 3600
    duration_str = format_duration(wait_seconds)

    if wait_hours < 1:
        # Quick turnaround - just acknowledge
        return FollowUpQuestion(
            question_type="quick_turnaround",
            text="That was quick! 🙌",
            subtext=f"{duration_str}" + (f" at {facility_name}" if facility_name else ""),
            options=[
                FollowUpOption(emoji="👍", label="Nice", value="positive")
            ],
            skippable=True,
            auto_dismiss_seconds=3
        )

    elif wait_hours < 2:
        # Normal wait - just acknowledge
        return FollowUpQuestion(
            question_type="normal_turnaround",
            text="Not bad! Drive safe 🚛",
            subtext=f"{duration_str}" + (f" at {facility_name}" if facility_name else ""),
            options=[
                FollowUpOption(emoji="👍", label="Thanks", value="acknowledged")
            ],
            skippable=True,
            auto_dismiss_seconds=3
        )

    elif wait_hours < 4:
        # Long wait - ask about detention
        return FollowUpQuestion(
            question_type="detention_payment",
            text=f"{duration_str}. Getting paid for that?",
            subtext=facility_name,
            options=[
                FollowUpOption(emoji="💰", label="Yep", value="paid"),
                FollowUpOption(emoji="😤", label="Nope", value="unpaid"),
                FollowUpOption(emoji="🤷", label="TBD", value="unknown")
            ],
            skippable=True
        )

    else:
        # Very long wait - empathize and ask
        return FollowUpQuestion(
            question_type="detention_payment_brutal",
            text=f"{duration_str}. Brutal. Detention pay?",
            subtext=facility_name,
            options=[
                FollowUpOption(emoji="💰", label="Yeah", value="paid"),
                FollowUpOption(emoji="🖕", label="Hell no", value="unpaid"),
                FollowUpOption(emoji="🤷", label="Fighting for it", value="disputed")
            ],
            skippable=True
        )


def build_parking_safety_question() -> FollowUpQuestion:
    """Build parking safety question"""
    return FollowUpQuestion(
        question_type="parking_safety",
        text="Sleep easy tonight?",
        subtext=None,
        options=[
            FollowUpOption(emoji="😴", label="Yeah", value="safe"),
            FollowUpOption(emoji="😬", label="Nah", value="sketchy")
        ],
        skippable=True
    )


def build_parking_vibe_question() -> FollowUpQuestion:
    """Build parking spot vibe question (on exit from parked)"""
    return FollowUpQuestion(
        question_type="parking_vibe",
        text="Nice! How's the spot?",
        subtext=None,
        options=[
            FollowUpOption(emoji="😴", label="Chill Vibes", value="chill"),
            FollowUpOption(emoji="😐", label="It's Fine", value="fine"),
            FollowUpOption(emoji="😬", label="Sketch AF", value="sketch")
        ],
        skippable=True
    )


def build_ready_to_roll_question() -> FollowUpQuestion:
    """Build morning readiness question"""
    return FollowUpQuestion(
        question_type="ready_to_roll",
        text="Ready to roll?",
        subtext=None,
        options=[
            FollowUpOption(emoji="☕", label="Coffee'd up", value="energized"),
            FollowUpOption(emoji="😴", label="Need more sleep", value="tired"),
            FollowUpOption(emoji="💪", label="Let's go", value="motivated")
        ],
        skippable=True
    )


def build_parking_spot_question(facility_name: Optional[str] = None) -> FollowUpQuestion:
    """Build parking spot assessment question (asked on ENTRY to parked)"""
    return FollowUpQuestion(
        question_type="parking_spot_entry",
        text="How's the spot?",
        subtext=facility_name,
        options=[
            FollowUpOption(emoji="😴", label="Solid", value="solid"),
            FollowUpOption(emoji="😐", label="Meh", value="meh"),
            FollowUpOption(emoji="😬", label="Sketch", value="sketch")
        ],
        skippable=True
    )


def build_facility_flow_question(facility_name: Optional[str] = None) -> FollowUpQuestion:
    """Build facility flow assessment question (asked on ENTRY to waiting)"""
    return FollowUpQuestion(
        question_type="facility_flow_entry",
        text="How's it looking?",
        subtext=facility_name,
        options=[
            FollowUpOption(emoji="🏃", label="Moving", value="moving"),
            FollowUpOption(emoji="🐢", label="Slow", value="slow"),
            FollowUpOption(emoji="🧊", label="Dead", value="dead"),
            FollowUpOption(emoji="🤷", label="Just got here", value="just_arrived")
        ],
        skippable=True
    )


def build_drive_safe_message() -> FollowUpQuestion:
    """Build simple encouragement message (no response needed)"""
    return FollowUpQuestion(
        question_type="drive_safe",
        text="Drive safe! 🚛",
        subtext=None,
        options=[
            FollowUpOption(emoji="👍", label="Thanks", value="acknowledged")
        ],
        skippable=True,
        auto_dismiss_seconds=2
    )


# ============================================================================
# First-Time User Welcome Questions
# ============================================================================

def build_first_time_parked_question() -> FollowUpQuestion:
    """Welcome message for first-time user who parked"""
    return FollowUpQuestion(
        question_type="first_time_parked",
        text="Welcome to Find a Truck Driver! 🚛",
        subtext="How's the spot?",
        options=[
            FollowUpOption(emoji="😴", label="Solid", value="solid", description="Your input helps other drivers find safe spots"),
            FollowUpOption(emoji="😐", label="Meh", value="meh"),
            FollowUpOption(emoji="😬", label="Sketch", value="sketch")
        ],
        skippable=True
    )


def build_first_time_waiting_question(facility_name: Optional[str] = None) -> FollowUpQuestion:
    """Welcome message for first-time user who's waiting"""
    return FollowUpQuestion(
        question_type="first_time_waiting",
        text="Welcome to Find a Truck Driver! 🚛",
        subtext="How's it looking?" + (f" at {facility_name}" if facility_name else ""),
        options=[
            FollowUpOption(emoji="🏃", label="Moving", value="moving", description="Help others know what to expect here"),
            FollowUpOption(emoji="🐢", label="Slow", value="slow"),
            FollowUpOption(emoji="🧊", label="Dead", value="dead"),
            FollowUpOption(emoji="🤷", label="Just got here", value="just_arrived")
        ],
        skippable=True
    )


def build_first_time_rolling_message() -> FollowUpQuestion:
    """Welcome message for first-time user who's rolling"""
    return FollowUpQuestion(
        question_type="first_time_rolling",
        text="Welcome to Find a Truck Driver! 🚛",
        subtext="You're on the map. Drive safe!",
        options=[
            FollowUpOption(emoji="👍", label="Thanks", value="acknowledged", description="Other truckers nearby can now see you rolling")
        ],
        skippable=True,
        auto_dismiss_seconds=3
    )


# ============================================================================
# Returning User Welcome Questions
# ============================================================================

def build_returning_user_question(
    new_status: str,
    days_away: int,
    facility_name: Optional[str] = None
) -> FollowUpQuestion:
    """Welcome back message for returning users (24+ hours away)"""

    # Greeting based on time away
    if days_away == 1:
        greeting = "Hey, welcome back!"
    elif days_away < 7:
        greeting = f"Back at it! Been {days_away} days."
    elif days_away < 30:
        greeting = "Good to see you again!"
    else:
        greeting = "Welcome back, driver!"

    if new_status == "parked":
        return FollowUpQuestion(
            question_type="returning_parked",
            text=greeting,
            subtext="How's the spot?",
            options=[
                FollowUpOption(emoji="😴", label="Solid", value="solid"),
                FollowUpOption(emoji="😐", label="Meh", value="meh"),
                FollowUpOption(emoji="😬", label="Sketch", value="sketch")
            ],
            skippable=True
        )

    elif new_status == "waiting":
        return FollowUpQuestion(
            question_type="returning_waiting",
            text=greeting,
            subtext="How's it looking?" + (f" at {facility_name}" if facility_name else ""),
            options=[
                FollowUpOption(emoji="🏃", label="Moving", value="moving"),
                FollowUpOption(emoji="🐢", label="Slow", value="slow"),
                FollowUpOption(emoji="🧊", label="Dead", value="dead"),
                FollowUpOption(emoji="🤷", label="Just got here", value="just_arrived")
            ],
            skippable=True
        )

    else:  # rolling
        return FollowUpQuestion(
            question_type="returning_rolling",
            text=f"{greeting} 🚛",
            subtext="You're on the map. Drive safe!",
            options=[
                FollowUpOption(emoji="👍", label="Thanks", value="acknowledged")
            ],
            skippable=True,
            auto_dismiss_seconds=3
        )


# ============================================================================
# Check-In Questions (Same Status)
# ============================================================================

def build_checkin_parked_short() -> FollowUpQuestion:
    """Check-in for parked status (short time, < 2 hours)"""
    return FollowUpQuestion(
        question_type="checkin_parked_short",
        text="✓ Location updated",
        subtext=None,
        options=[
            FollowUpOption(emoji="👍", label="OK", value="acknowledged")
        ],
        skippable=True,
        auto_dismiss_seconds=2
    )


def build_checkin_parked_long() -> FollowUpQuestion:
    """Check-in for parked status (long time, 2+ hours)"""
    return FollowUpQuestion(
        question_type="checkin_parked_long",
        text="Still here? Spot still good?",
        subtext=None,
        options=[
            FollowUpOption(emoji="😴", label="Solid", value="solid", description="Things can change - lot gets sketchy at night"),
            FollowUpOption(emoji="😐", label="Meh", value="meh"),
            FollowUpOption(emoji="😬", label="Sketch", value="sketch")
        ],
        skippable=True
    )


def build_checkin_waiting() -> FollowUpQuestion:
    """Check-in for waiting status"""
    return FollowUpQuestion(
        question_type="checkin_waiting",
        text="Still waiting. How's it now?",
        subtext=None,
        options=[
            FollowUpOption(emoji="🏃", label="Moving now", value="moving", description="This is valuable - facility status changes over time"),
            FollowUpOption(emoji="🐢", label="Slow", value="slow"),
            FollowUpOption(emoji="🧊", label="Still dead", value="dead")
        ],
        skippable=True
    )


def build_checkin_rolling() -> FollowUpQuestion:
    """Check-in for rolling status"""
    return FollowUpQuestion(
        question_type="checkin_rolling",
        text="✓ Location updated",
        subtext=None,
        options=[
            FollowUpOption(emoji="👍", label="OK", value="acknowledged")
        ],
        skippable=True,
        auto_dismiss_seconds=1
    )


# ============================================================================
# WAITING → PARKED Transition Questions
# ============================================================================

def build_calling_it_a_night_question() -> FollowUpQuestion:
    """WAITING → PARKED at same location - check if sleeping or still waiting"""
    return FollowUpQuestion(
        question_type="calling_it_a_night",
        text="Calling it a night?",
        subtext=None,
        options=[
            FollowUpOption(emoji="😴", label="Yep, done", value="sleeping"),
            FollowUpOption(emoji="⏳", label="Still waiting", value="still_waiting")
        ],
        skippable=True
    )


def build_done_at_facility_question(facility_name: str, wait_seconds: int) -> FollowUpQuestion:
    """WAITING → PARKED nearby - ask about detention payment"""
    duration_str = format_duration(wait_seconds)
    return FollowUpQuestion(
        question_type="done_at_facility_detention",
        text=f"Done at {facility_name}. Getting paid for the wait?",
        subtext=f"{duration_str}",
        options=[
            FollowUpOption(emoji="💰", label="Yep", value="paid"),
            FollowUpOption(emoji="😤", label="Nope", value="unpaid")
        ],
        skippable=True
    )


# ============================================================================
# PARKED → WAITING Transition Questions
# ============================================================================

def build_time_to_work_question(facility_name: Optional[str] = None) -> FollowUpQuestion:
    """PARKED → WAITING - driver woke up and ready to work"""
    return FollowUpQuestion(
        question_type="time_to_work",
        text="Time to work! How's it looking?",
        subtext=facility_name,
        options=[
            FollowUpOption(emoji="🏃", label="Moving", value="moving"),
            FollowUpOption(emoji="🐢", label="Slow", value="slow"),
            FollowUpOption(emoji="🧊", label="Dead", value="dead"),
            FollowUpOption(emoji="🤷", label="Just started", value="just_arrived")
        ],
        skippable=True
    )


# ============================================================================
# Weather-Related Questions
# ============================================================================

def build_weather_alert_question(alert_event: str, alert_headline: str, emoji: str) -> FollowUpQuestion:
    """Severe weather alert - ask if driver is safe"""
    return FollowUpQuestion(
        question_type="weather_alert",
        text=f"{emoji} {alert_event}",
        subtext=alert_headline,
        options=[
            FollowUpOption(emoji="👍", label="I'm safe", value="safe"),
            FollowUpOption(emoji="⚠️", label="Pulling over", value="stopping"),
            FollowUpOption(emoji="🏠", label="Already parked", value="parked")
        ],
        skippable=True
    )


def build_weather_check_question(weather_summary: str) -> FollowUpQuestion:
    """Ask driver about road conditions in bad weather"""
    return FollowUpQuestion(
        question_type="weather_road_conditions",
        text="Roads okay out there?",
        subtext=weather_summary,
        options=[
            FollowUpOption(emoji="👍", label="All good", value="good"),
            FollowUpOption(emoji="😬", label="Sketchy", value="bad"),
            FollowUpOption(emoji="⚠️", label="Dangerous", value="dangerous")
        ],
        skippable=True
    )


def build_weather_stay_safe_message(weather_summary: str) -> FollowUpQuestion:
    """Encourage driver to stay parked during severe weather"""
    return FollowUpQuestion(
        question_type="weather_stay_safe",
        text=f"Storm nearby. Stay safe!",
        subtext=weather_summary,
        options=[
            FollowUpOption(emoji="👍", label="Will do", value="acknowledged")
        ],
        skippable=True,
        auto_dismiss_seconds=3
    )


def build_weather_good_message(new_status: str) -> FollowUpQuestion:
    """Show positive weather message when conditions are good"""
    if new_status == "rolling":
        text = "Clear skies ahead! ☀️"
        subtext = "Perfect driving weather"
    elif new_status == "waiting":
        text = "Nice weather today! 🌤️"
        subtext = "Good conditions"
    else:  # parked
        text = "Weather looking good! 🌤️"
        subtext = "Enjoy your rest"

    return FollowUpQuestion(
        question_type="weather_good",
        text=text,
        subtext=subtext,
        options=[
            FollowUpOption(emoji="👍", label="Thanks", value="acknowledged")
        ],
        skippable=True,
        auto_dismiss_seconds=3
    )
