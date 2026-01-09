# Follow-Up Questions Implementation - Phase 1 MVP

## Status: 100% Complete ✅

### What's Been Built

#### ✅ 1. Database Schema (Migration 004)
- **status_updates** table - Tracks status changes with full context
- **facility_metrics** table - Aggregated detention/safety data
- **Helper function** - `get_previous_status()` for quick lookups
- **RLS policies** - Proper security for driver data

**Location:** `migrations/004_add_status_updates.sql`

**Run:** Already applied ✅

#### ✅ 2. Pydantic Models
- `FollowUpOption` - Individual answer choices
- `FollowUpQuestion` - Complete question structure
- `StatusContext` - Transition context data
- `FollowUpResponse` - Answer recording model
- **Helper functions** - Question builders for each scenario

**Location:** `app/models/follow_up.py`

#### ✅ 3. Context Engine
- `FollowUpEngine` class - Decision tree logic
- Context calculation - Time/distance from previous status
- **Phase 1 MVP flows implemented:**
  - 🔴 WAITING → 🟢 ROLLING (detention tracking)
  - 🔵 PARKED → 🟢 ROLLING (parking safety/vibe)

**Location:** `app/services/follow_up_engine.py`

#### ✅ 4. Status Update Endpoint Integration

Modified the existing status update endpoint to return follow-up questions.

**Location:** [app/routers/drivers.py:215-369](../app/routers/drivers.py)

**Key Changes:**
- Changed response model from `Driver` to `StatusUpdateWithFollowUp`
- Added optional `latitude` and `longitude` to `StatusUpdate` model
- Query previous status from `status_updates` table
- Calculate context using `determine_follow_up()` engine
- Find facility at current location (within 0.3 miles)
- Save complete `status_update` record with context and question
- Return follow-up question (if any) in response

**Endpoint:** `POST /api/v1/drivers/me/status`

#### ✅ 5. Follow-Up Response Recording

Created new router with endpoints to record and view follow-up responses.

**Location:** [app/routers/follow_ups.py](../app/routers/follow_ups.py)

**Endpoints:**
- `POST /api/v1/follow-ups/respond` - Record driver's answer
- `GET /api/v1/follow-ups/history` - View driver's follow-up history

**Features:**
- Verify status_update belongs to driver
- Prevent duplicate responses
- Record timestamp of response
- Return success confirmation

#### ✅ 6. API Documentation

Complete API documentation with examples and testing guide.

**Location:** [docs/FOLLOW_UP_API_GUIDE.md](./FOLLOW_UP_API_GUIDE.md)

---

---

## Implementation Complete! 🎉

All backend work is finished. The system is ready for:

1. **Frontend Integration**
   - Use the comprehensive guide in [FOLLOW_UP_API_GUIDE.md](./FOLLOW_UP_API_GUIDE.md)
   - React component examples included
   - CSS styling examples provided

2. **Testing with Real Data**
   - Use curl commands from the guide
   - Test all question types
   - Verify database records

3. **Phase 2 Planning**
   - Add more status transitions
   - Build facility metrics aggregation
   - Create public facility scorecards

---

## Summary

**Phase 1 MVP is 100% complete!** 🎉

The foundation is solid:
- ✅ Database schema
- ✅ Pydantic models
- ✅ Context engine
- ✅ Two high-value flows implemented
- ✅ Status update endpoint integrated
- ✅ Response recording endpoint
- ✅ Complete API documentation

This captures the **highest value data** (detention times and payment) with **minimal user friction** (one skippable tap).

The intelligence engine is built to scale - adding more transitions in Phase 2 is just adding more handlers to the decision tree.

**For complete API usage, testing, and integration:**
👉 See [FOLLOW_UP_API_GUIDE.md](./FOLLOW_UP_API_GUIDE.md)

---

## ~~Old Planning Notes~~ (Historical Reference)

<details>
<summary>Click to expand original planning notes (now completed)</summary>

### ~~5. Response Recording Endpoint (Todo)~~

Create new endpoint to record follow-up answers:

**File to create:** `app/routers/follow_ups.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.follow_up import FollowUpResponse
from app.dependencies import get_current_driver
from supabase import Client
from app.database import get_db_admin
from datetime import datetime

router = APIRouter(prefix="/follow-ups", tags=["Follow-Up Questions"])

@router.post("/respond")
async def record_follow_up_response(
    response: FollowUpResponse,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Record driver's response to a follow-up question.
    Updates the status_update record with their answer.
    """

    # Verify this status_update belongs to this driver
    status_update = db.from_("status_updates")\
        .select("*")\
        .eq("id", response.status_update_id)\
        .eq("driver_id", driver["id"])\
        .single()\
        .execute()

    if not status_update.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status update not found"
        )

    # Update with response
    db.from_("status_updates").update({
        "follow_up_response": response.response_value,
        "follow_up_response_text": response.response_text,
        "follow_up_answered_at": datetime.utcnow().isoformat()
    }).eq("id", response.status_update_id).execute()

    # TODO: Update facility_metrics in background job

    return {"success": True, "message": "Response recorded"}
```

**Register router in `app/main.py`:**

```python
from app.routers import follow_ups

app.include_router(follow_ups.router, prefix="/api/v1")
```

---

## Testing Plan

### Test 1: WAITING → ROLLING (< 1 hour)

```bash
# 1. Update to WAITING
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "waiting"}'

# Wait 30 minutes (or manipulate DB timestamp)

# 2. Update to ROLLING
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "rolling"}'

# Expected response:
{
  "status_update_id": "uuid",
  "status": "rolling",
  "prev_status": "waiting",
  "follow_up_question": {
    "question_type": "quick_turnaround",
    "text": "That was quick! 🙌",
    "subtext": "30 min",
    "options": [{"emoji": "👍", "label": "Nice", "value": "positive"}],
    "skippable": true,
    "auto_dismiss_seconds": 3
  }
}
```

### Test 2: WAITING → ROLLING (3 hours)

```bash
# Manipulate DB to set prev_updated_at to 3 hours ago
UPDATE status_updates
SET created_at = NOW() - INTERVAL '3 hours'
WHERE driver_id = 'your-driver-id'
ORDER BY created_at DESC
LIMIT 1;

# Then update status
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "rolling"}'

# Expected:
{
  "follow_up_question": {
    "question_type": "detention_payment",
    "text": "3 hrs 0 min. Getting paid for that?",
    "options": [
      {"emoji": "💰", "label": "Yep", "value": "paid"},
      {"emoji": "😤", "label": "Nope", "value": "unpaid"},
      {"emoji": "🤷", "label": "TBD", "value": "unknown"}
    ]
  }
}
```

### Test 3: PARKED → ROLLING (8 hours)

```bash
# 1. Park overnight
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "parked"}'

# Wait 8 hours (or manipulate timestamp)

# 2. Start rolling
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "rolling"}'

# Expected:
{
  "follow_up_question": {
    "question_type": "parking_vibe",
    "text": "Nice! How's the spot?",
    "options": [
      {"emoji": "😴", "label": "Chill Vibes", "value": "chill"},
      {"emoji": "😐", "label": "It's Fine", "value": "fine"},
      {"emoji": "😬", "label": "Sketch AF", "value": "sketch"}
    ]
  }
}
```

### Test 4: Record Response

```bash
curl -X POST http://localhost:8000/api/v1/follow-ups/respond \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "status_update_id": "uuid-from-above",
    "response_value": "paid"
  }'

# Expected:
{
  "success": true,
  "message": "Response recorded"
}
```

---

## Frontend Integration

### Status Update Flow

```typescript
interface FollowUpQuestion {
  question_type: string;
  text: string;
  subtext?: string;
  options: Array<{
    emoji: string;
    label: string;
    value: string;
  }>;
  skippable: boolean;
  auto_dismiss_seconds?: number;
}

async function updateStatus(newStatus: string, location: LatLng) {
  const response = await fetch('/api/v1/drivers/me/status', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      status: newStatus,
      latitude: location.lat,
      longitude: location.lng
    })
  });

  const data = await response.json();

  // Show follow-up question if present
  if (data.follow_up_question) {
    showFollowUpModal(data.status_update_id, data.follow_up_question);
  }
}
```

### Modal Component

```tsx
function FollowUpModal({ statusUpdateId, question, onClose }: Props) {
  const handleResponse = async (value: string) => {
    await fetch('/api/v1/follow-ups/respond', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        status_update_id: statusUpdateId,
        response_value: value
      })
    });
    onClose();
  };

  // Auto-dismiss if configured
  useEffect(() => {
    if (question.auto_dismiss_seconds) {
      const timer = setTimeout(onClose, question.auto_dismiss_seconds * 1000);
      return () => clearTimeout(timer);
    }
  }, [question.auto_dismiss_seconds]);

  return (
    <div className="follow-up-modal">
      <h3>{question.text}</h3>
      {question.subtext && <p className="subtext">{question.subtext}</p>}

      <div className="options">
        {question.options.map(option => (
          <button
            key={option.value}
            onClick={() => handleResponse(option.value)}
            className="option-button"
          >
            <span className="emoji">{option.emoji}</span>
            <span className="label">{option.label}</span>
          </button>
        ))}
      </div>

      {question.skippable && (
        <button onClick={onClose} className="skip-button">Skip</button>
      )}
    </div>
  );
}
```

---

## Analytics Queries

### Detention Stats by Facility

```sql
SELECT
  f.name AS facility_name,
  f.city,
  f.state,
  COUNT(*) AS total_reports,
  AVG(su.time_since_last_seconds / 60) AS avg_wait_minutes,
  COUNT(CASE WHEN su.follow_up_response = 'paid' THEN 1 END) AS paid_count,
  COUNT(CASE WHEN su.follow_up_response = 'unpaid' THEN 1 END) AS unpaid_count,
  ROUND(
    100.0 * COUNT(CASE WHEN su.follow_up_response = 'paid' THEN 1 END) /
    NULLIF(COUNT(*), 0),
    1
  ) AS detention_paid_pct
FROM status_updates su
JOIN facilities f ON f.id = su.facility_id
WHERE su.prev_status = 'waiting'
  AND su.status = 'rolling'
  AND su.follow_up_question_type LIKE 'detention%'
  AND su.follow_up_response IS NOT NULL
GROUP BY f.id, f.name, f.city, f.state
HAVING COUNT(*) >= 5  -- At least 5 reports
ORDER BY avg_wait_minutes DESC;
```

### Parking Safety by Location

```sql
SELECT
  f.name,
  f.city,
  f.state,
  COUNT(*) AS total_reports,
  COUNT(CASE WHEN su.follow_up_response IN ('chill', 'fine') THEN 1 END) AS safe_count,
  COUNT(CASE WHEN su.follow_up_response = 'sketch' THEN 1 END) AS unsafe_count,
  ROUND(
    100.0 * COUNT(CASE WHEN su.follow_up_response IN ('chill', 'fine') THEN 1 END) /
    NULLIF(COUNT(*), 0),
    1
  ) AS safety_percentage
FROM status_updates su
JOIN facilities f ON f.id = su.facility_id
WHERE su.follow_up_question_type = 'parking_vibe'
  AND su.follow_up_response IS NOT NULL
GROUP BY f.id, f.name, f.city, f.state
HAVING COUNT(*) >= 3
ORDER BY safety_percentage DESC;
```

---

## Next Steps

1. **Complete endpoint modifications** (30 minutes)
   - Update `update_driver_status` endpoint
   - Create follow-up response endpoint

2. **Test the flow** (30 minutes)
   - Test WAITING → ROLLING scenarios
   - Test PARKED → ROLLING scenarios
   - Verify database records

3. **Frontend integration** (2-3 hours)
   - Create follow-up modal component
   - Integrate with status update flow
   - Add styling

4. **Phase 2 expansion** (future)
   - Add remaining transitions
   - Build facility metrics aggregation job
   - Create public facility scorecards

---

</details>

---

**For the most up-to-date API documentation, testing procedures, and frontend integration examples, please refer to:**

📚 **[FOLLOW_UP_API_GUIDE.md](./FOLLOW_UP_API_GUIDE.md)** - Complete API documentation with testing guide and React examples
