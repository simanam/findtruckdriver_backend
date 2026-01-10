# Weather + Regular Follow-Up Questions

## Overview

The system now returns **TWO separate questions** in every status update response:

1. **`follow_up_question`** - Primary question (detention, parking quality, facility flow, etc.)
2. **`weather_info`** - Weather information (always shown - good or bad)

This allows us to:
- ✅ **Always show weather** to keep drivers engaged and informed
- ✅ **Still collect valuable data** even during severe weather
- ✅ **Show positive weather** ("Clear skies! ☀️") when conditions are good
- ✅ **Critical safety alerts** when weather is severe

---

## What Changed

### Backend Changes

#### 1. New Weather Question Type

Added `build_weather_good_message()` in [follow_up.py](../app/models/follow_up.py):

```python
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
```

#### 2. New `get_weather_info()` Function

Created standalone function in [follow_up_engine.py](../app/services/follow_up_engine.py):

```python
def get_weather_info(
    new_status: str,
    latitude: float,
    longitude: float
) -> Optional[FollowUpQuestion]:
    """
    Get weather information (good or bad) for display.

    ALWAYS shown (when available) and does NOT replace regular follow-up questions.
    Returns weather message for all conditions:
    - Severe weather: Alert with safety check
    - Moderate weather: Informational
    - Good weather: Positive message
    """
    try:
        alerts = get_weather_alerts(latitude, longitude)

        if alerts:
            most_severe = get_most_severe_alert(alerts)
            if most_severe:
                # Show different messages based on severity
                if most_severe.severity in ["Severe", "Extreme"]:
                    # CRITICAL: Always show
                    if new_status == "rolling":
                        return build_weather_alert_question(...)
                    elif new_status == "waiting":
                        return build_weather_check_question(...)
                    else:  # parked
                        return build_weather_stay_safe_message(...)

                elif most_severe.severity == "Moderate":
                    # MODERATE: Show to rolling/waiting only
                    if new_status in ["rolling", "waiting"]:
                        return build_weather_check_question(...)

        # No alerts - show positive message
        return build_weather_good_message(new_status)

    except Exception as e:
        logger.error(f"Weather check failed: {e}")
        return None
```

#### 3. Updated `determine_follow_up()`

Now returns **three** values instead of two:

**Before:**
```python
def determine_follow_up(...) -> Tuple[StatusContext, Optional[FollowUpQuestion]]:
    # ...
    return context, question
```

**After:**
```python
def determine_follow_up(...) -> Tuple[StatusContext, Optional[FollowUpQuestion], Optional[FollowUpQuestion]]:
    # Get primary question (NOT weather)
    primary_question = engine.get_follow_up_question(...)

    # Get weather info separately (ALWAYS check)
    weather_question = get_weather_info(...)

    return context, primary_question, weather_question
```

#### 4. Updated Response Model

Added `weather_info` field to [StatusUpdateWithFollowUp](../app/models/follow_up.py):

```python
class StatusUpdateWithFollowUp(BaseModel):
    """Status update response with optional follow-up question and weather info"""
    status_update_id: UUID
    status: str
    prev_status: Optional[str] = None
    context: Optional[StatusContext] = None
    follow_up_question: Optional[FollowUpQuestion] = None
    weather_info: Optional[FollowUpQuestion] = None  # NEW!
    message: str
```

#### 5. Updated Endpoints

Both `/api/v1/drivers/me/status` and `/api/v1/locations/status/update` now:

```python
# Get both questions
context, question, weather_info = determine_follow_up(...)

# Return both in response
return StatusUpdateWithFollowUp(
    status_update_id=status_record.id,
    status=status_update.status,
    prev_status=prev["status"] if prev else None,
    context=context,
    follow_up_question=question,
    weather_info=weather_info,  # NEW!
    message="Status updated successfully"
)
```

---

## API Response Examples

### Example 1: Good Weather + Parking Question

```json
POST /api/v1/drivers/me/status
{
  "status": "parked",
  "latitude": 36.7594,
  "longitude": -120.0247
}

Response:
{
  "status_update_id": "uuid-here",
  "status": "parked",
  "prev_status": "rolling",
  "follow_up_question": {
    "question_type": "parking_spot_entry",
    "text": "How's the spot?",
    "subtext": "Pilot Travel Center",
    "options": [
      {"emoji": "😴", "label": "Solid", "value": "solid"},
      {"emoji": "😐", "label": "Meh", "value": "meh"},
      {"emoji": "😬", "label": "Sketch", "value": "sketch"}
    ],
    "skippable": true,
    "auto_dismiss_seconds": null
  },
  "weather_info": {
    "question_type": "weather_good",
    "text": "Weather looking good! 🌤️",
    "subtext": "Enjoy your rest",
    "options": [
      {"emoji": "👍", "label": "Thanks", "value": "acknowledged"}
    ],
    "skippable": true,
    "auto_dismiss_seconds": 3
  },
  "message": "Status updated successfully"
}
```

### Example 2: Severe Weather + Detention Question

```json
POST /api/v1/drivers/me/status
{
  "status": "rolling",
  "latitude": 41.3114,
  "longitude": -105.5911
}

Response:
{
  "status_update_id": "uuid-here",
  "status": "rolling",
  "prev_status": "waiting",
  "follow_up_question": {
    "question_type": "detention_payment",
    "text": "Did you get detention pay?",
    "subtext": "Waited 3 hours",
    "options": [
      {"emoji": "💰", "label": "Yep", "value": "yes"},
      {"emoji": "😤", "label": "Nope", "value": "no"}
    ],
    "skippable": true
  },
  "weather_info": {
    "question_type": "weather_alert",
    "text": "❄️ Winter Storm Warning",
    "subtext": "Heavy snow expected. Travel may become dangerous...",
    "options": [
      {"emoji": "👍", "label": "I'm safe", "value": "safe"},
      {"emoji": "⚠️", "label": "Pulling over", "value": "stopping"},
      {"emoji": "🏠", "label": "Already parked", "value": "parked"}
    ],
    "skippable": true
  },
  "message": "Status updated successfully"
}
```

### Example 3: Only Weather (No Follow-Up)

```json
POST /api/v1/drivers/me/status
{
  "status": "rolling",
  "latitude": 36.7594,
  "longitude": -120.0247
}

Response:
{
  "status_update_id": "uuid-here",
  "status": "rolling",
  "prev_status": "rolling",
  "follow_up_question": null,  // Check-in, no question needed
  "weather_info": {
    "question_type": "weather_good",
    "text": "Clear skies ahead! ☀️",
    "subtext": "Perfect driving weather",
    "options": [
      {"emoji": "👍", "label": "Thanks", "value": "acknowledged"}
    ],
    "skippable": true,
    "auto_dismiss_seconds": 3
  },
  "message": "Status updated successfully"
}
```

---

## Question Types

### Primary Follow-Up Questions

These collect valuable data:
- `parking_spot_entry` - Parking quality
- `facility_flow_entry` - Facility wait times
- `detention_payment` - Detention tracking
- `calling_it_a_night` - Status correction
- `first_time_parked` - First-time user welcome
- `returning_parked` - Returning user greeting
- etc.

### Weather Question Types

New weather-specific types:
- `weather_alert` - **Severe/Extreme** weather (requires response)
- `weather_road_conditions` - **Moderate** weather (road check)
- `weather_stay_safe` - **Any severity** for parked drivers (encouragement)
- `weather_good` - **No alerts** (positive message) ⭐ NEW!

---

## Frontend Integration

### Display Strategy

**Option A: Sequential (Recommended)**
1. Show weather message first (auto-dismiss after 3s if good weather)
2. Then show primary follow-up question
3. Collect both responses separately

**Option B: Combined View**
1. Show weather as a banner/toast at top
2. Show primary question below
3. Both visible simultaneously

### Implementation Example

```typescript
interface StatusUpdateResponse {
  status_update_id: string;
  status: string;
  follow_up_question?: FollowUpQuestion;
  weather_info?: FollowUpQuestion;  // NEW!
  message: string;
}

async function handleStatusUpdate(response: StatusUpdateResponse) {
  // Show weather first
  if (response.weather_info) {
    await showWeatherModal(response.weather_info);
    // Auto-dismiss after 3s for good weather
  }

  // Then show primary question
  if (response.follow_up_question) {
    await showFollowUpModal(response.follow_up_question);
  }
}
```

### Recording Responses

**Important:** Both questions should be recorded separately!

```typescript
// Record weather response
await api.post('/api/v1/follow-ups/respond', {
  status_update_id: response.status_update_id,
  response_value: 'acknowledged',  // From weather_info
  question_type: 'weather_good'
});

// Record primary question response
await api.post('/api/v1/follow-ups/respond', {
  status_update_id: response.status_update_id,
  response_value: 'solid',  // From follow_up_question
  question_type: 'parking_spot_entry'
});
```

---

## Benefits

### 1. Always-On Weather Engagement
- Drivers see weather info on **every** status update
- Creates habit of checking weather
- Positive messages keep them engaged

### 2. Continuous Data Collection
- Severe weather doesn't block data collection
- We still get detention times, parking quality, facility flow
- More complete dataset

### 3. Safety + Data
- Critical weather alerts shown immediately
- But detention/parking questions still asked
- Driver can respond to both

### 4. Better UX
- "Clear skies! ☀️" is more engaging than nothing
- Auto-dismiss for non-critical messages
- Doesn't feel repetitive

---

## Migration Notes

### Database

No schema changes needed! Weather responses use the same `follow_up_response` fields.

### Existing Clients

**Backward compatible!** Old clients will:
- Still see `follow_up_question` (primary question)
- Ignore `weather_info` field (gracefully handled)
- Continue working as before

New clients can:
- Show both questions
- Create better UX with weather animations
- Collect more comprehensive data

---

## Testing

### Manual Test Scenarios

1. **Good weather + parking**
   - Status: rolling → parked
   - Location: Clear weather area
   - Expected: "Clear skies!" + "How's the spot?"

2. **Severe weather + detention**
   - Status: waiting (2hrs) → rolling
   - Location: Winter storm area
   - Expected: "Winter Storm Warning" + "Did you get detention?"

3. **Moderate weather + parked**
   - Status: rolling → parked
   - Location: Freeze warning area
   - Expected: "Weather looking good!" + "How's the spot?"
   - (Moderate alerts not shown to parked drivers)

4. **Check-in + weather**
   - Status: rolling → rolling (check-in)
   - Location: Any
   - Expected: No primary question + weather message only

---

## Summary

**Key Changes:**
- ✅ `determine_follow_up()` returns 3 values now (context, question, weather)
- ✅ Added `get_weather_info()` function
- ✅ Added `build_weather_good_message()` builder
- ✅ Updated `StatusUpdateWithFollowUp` model
- ✅ Updated both status update endpoints
- ✅ Weather is ALWAYS checked and shown
- ✅ Primary questions still collected regardless of weather

**Result:**
Drivers get weather info on every update (good or bad) + we still collect valuable data even during severe weather! 🎉
