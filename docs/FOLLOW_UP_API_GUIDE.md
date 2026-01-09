# Follow-Up Questions API - Complete Guide

## Status: ✅ 100% Complete

The intelligent follow-up questions system is now fully integrated into the backend!

---

## Overview

After a driver updates their status, the system may present a contextual follow-up question based on:
- Previous status and location
- Time elapsed since last status
- Distance moved
- Current facility

**Phase 1 MVP covers two high-value flows:**
1. **WAITING → ROLLING**: Detention time and payment tracking
2. **PARKED → ROLLING**: Parking safety and vibe feedback

---

## API Endpoints

### 1. Update Status (with Follow-Up Intelligence)

**Endpoint:** `POST /api/v1/drivers/me/status`

**Request:**
```json
{
  "status": "rolling",
  "latitude": 36.8283,
  "longitude": -119.9193
}
```

**Notes:**
- `latitude` and `longitude` are **optional** but recommended
- If not provided, system will use last known location from `driver_locations`
- Without location, follow-up questions cannot be calculated

**Response (with follow-up question):**
```json
{
  "status_update_id": "uuid-here",
  "status": "rolling",
  "prev_status": "waiting",
  "context": {
    "prev_status": "waiting",
    "prev_latitude": 36.8283,
    "prev_longitude": -119.9193,
    "time_since_seconds": 10800,
    "distance_miles": 0.4,
    "time_since_hours": 3.0,
    "is_same_location": true,
    "is_nearby": true
  },
  "follow_up_question": {
    "question_type": "detention_payment",
    "text": "3 hrs 0 min. Getting paid for that?",
    "subtext": "Sysco Houston",
    "options": [
      {
        "emoji": "💰",
        "label": "Yep",
        "value": "paid",
        "description": null
      },
      {
        "emoji": "😤",
        "label": "Nope",
        "value": "unpaid",
        "description": null
      },
      {
        "emoji": "🤷",
        "label": "TBD",
        "value": "unknown",
        "description": null
      }
    ],
    "skippable": true,
    "auto_dismiss_seconds": null
  },
  "message": "Status updated successfully"
}
```

**Response (no follow-up question):**
```json
{
  "status_update_id": "uuid-here",
  "status": "rolling",
  "prev_status": "parked",
  "context": {
    "prev_status": "parked",
    "time_since_seconds": 300,
    "distance_miles": 15.2,
    "time_since_hours": 0.08,
    "is_same_location": false,
    "is_nearby": false
  },
  "follow_up_question": null,
  "message": "Status updated successfully"
}
```

---

### 2. Record Follow-Up Response

**Endpoint:** `POST /api/v1/follow-ups/respond`

**Request:**
```json
{
  "status_update_id": "uuid-from-status-update",
  "response_value": "paid",
  "response_text": null
}
```

**Response:**
```json
{
  "success": true,
  "message": "Response recorded successfully",
  "status_update_id": "uuid-here"
}
```

**Error Cases:**

- **404**: Status update not found or doesn't belong to you
- **400**: Status update has no follow-up question
- **400**: Follow-up already answered

---

### 3. Get Follow-Up History

**Endpoint:** `GET /api/v1/follow-ups/history?limit=50`

**Response:**
```json
{
  "count": 12,
  "history": [
    {
      "status_update_id": "uuid-1",
      "status": "rolling",
      "prev_status": "waiting",
      "created_at": "2026-01-09T12:00:00Z",
      "question_type": "detention_payment",
      "question_text": "3 hrs 0 min. Getting paid for that?",
      "response_value": "paid",
      "answered_at": "2026-01-09T12:00:15Z",
      "was_answered": true
    },
    {
      "status_update_id": "uuid-2",
      "status": "rolling",
      "prev_status": "parked",
      "created_at": "2026-01-09T08:30:00Z",
      "question_type": "parking_vibe",
      "question_text": "Nice! How's the spot?",
      "response_value": null,
      "answered_at": null,
      "was_answered": false
    }
  ]
}
```

---

## Question Types (Phase 1)

### Detention Flow (WAITING → ROLLING)

| Wait Time | Question Type | Text | Options | Auto-Dismiss |
|-----------|---------------|------|---------|--------------|
| < 1 hour | `quick_turnaround` | "That was quick! 🙌" | [👍 Nice] | 3 seconds |
| 1-2 hours | `normal_turnaround` | "Not bad! Drive safe 🚛" | [👍 Thanks] | 3 seconds |
| 2-4 hours | `detention_payment` | "X hrs Y min. Getting paid for that?" | [💰 Yep, 😤 Nope, 🤷 TBD] | No |
| 4+ hours | `detention_payment_brutal` | "X hrs Y min. Brutal. Detention pay?" | [💰 Yeah, 🖕 Hell no, 🤷 Fighting for it] | No |

**Conditions:**
- Only if still at facility (< 1 mile from previous location)
- Or nearby (1-10 miles) with wait time > 1 hour

### Parking Flow (PARKED → ROLLING)

| Parked Duration | Question Type | Text | Options | Auto-Dismiss |
|-----------------|---------------|------|---------|--------------|
| 6-14 hours | `parking_vibe` | "Nice! How's the spot?" | [😴 Chill Vibes, 😐 It's Fine, 😬 Sketch AF] | No |
| 14+ hours | `ready_to_roll` | "Ready to roll?" | [☕ Coffee'd up, 😴 Need more sleep, 💪 Let's go] | No |
| < 6 hours | None | - | - | - |

**Conditions:**
- Only if at same location (< 1 mile)

---

## Testing Guide

### Test 1: Quick Turnaround (< 1 hour)

```bash
# 1. Update to WAITING
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "waiting",
    "latitude": 36.8283,
    "longitude": -119.9193
  }'

# Wait 30 minutes (or manipulate DB timestamp for faster testing)
# To manipulate:
# psql -h localhost -U postgres -d finddriverdb
# UPDATE status_updates SET created_at = NOW() - INTERVAL '30 minutes'
# WHERE driver_id = 'your-driver-id' ORDER BY created_at DESC LIMIT 1;

# 2. Update to ROLLING (from same location)
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rolling",
    "latitude": 36.8283,
    "longitude": -119.9193
  }'

# Expected: "That was quick! 🙌" with auto-dismiss in 3 seconds
```

### Test 2: Detention Payment (3 hours)

```bash
# 1. Update to WAITING
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "waiting",
    "latitude": 36.8283,
    "longitude": -119.9193
  }'

# Manipulate timestamp to 3 hours ago
# UPDATE status_updates SET created_at = NOW() - INTERVAL '3 hours'
# WHERE driver_id = 'your-driver-id' ORDER BY created_at DESC LIMIT 1;

# 2. Update to ROLLING (still at same location)
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rolling",
    "latitude": 36.8283,
    "longitude": -119.9193
  }'

# Expected: "3 hrs 0 min. Getting paid for that?"
# Options: [💰 Yep, 😤 Nope, 🤷 TBD]
```

### Test 3: Parking Vibe (8 hours)

```bash
# 1. Park overnight
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "parked",
    "latitude": 36.8283,
    "longitude": -119.9193
  }'

# Manipulate timestamp to 8 hours ago
# UPDATE status_updates SET created_at = NOW() - INTERVAL '8 hours'
# WHERE driver_id = 'your-driver-id' ORDER BY created_at DESC LIMIT 1;

# 2. Start rolling (from same spot)
curl -X POST http://localhost:8000/api/v1/drivers/me/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rolling",
    "latitude": 36.8283,
    "longitude": -119.9193
  }'

# Expected: "Nice! How's the spot?"
# Options: [😴 Chill Vibes, 😐 It's Fine, 😬 Sketch AF]
```

### Test 4: Record Response

```bash
# Save the status_update_id from the response above, then:
curl -X POST http://localhost:8000/api/v1/follow-ups/respond \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status_update_id": "uuid-from-above",
    "response_value": "paid"
  }'

# Expected:
# {
#   "success": true,
#   "message": "Response recorded successfully"
# }
```

### Test 5: View History

```bash
curl -X GET http://localhost:8000/api/v1/follow-ups/history \
  -H "Authorization: Bearer $TOKEN"

# Expected: List of all follow-up questions you've received
```

---

## Frontend Integration

### React Example - Status Update with Modal

```typescript
import { useState } from 'react';

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

interface StatusUpdateResponse {
  status_update_id: string;
  status: string;
  follow_up_question: FollowUpQuestion | null;
  message: string;
}

function StatusButtons() {
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [followUpData, setFollowUpData] = useState<{
    statusUpdateId: string;
    question: FollowUpQuestion;
  } | null>(null);

  const updateStatus = async (newStatus: string) => {
    // Get current location
    const position = await getCurrentLocation();

    // Update status
    const response = await fetch('/api/v1/drivers/me/status', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        status: newStatus,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      })
    });

    const data: StatusUpdateResponse = await response.json();

    // Show follow-up modal if question present
    if (data.follow_up_question) {
      setFollowUpData({
        statusUpdateId: data.status_update_id,
        question: data.follow_up_question
      });
      setShowFollowUp(true);

      // Auto-dismiss if configured
      if (data.follow_up_question.auto_dismiss_seconds) {
        setTimeout(() => {
          setShowFollowUp(false);
        }, data.follow_up_question.auto_dismiss_seconds * 1000);
      }
    }
  };

  const handleFollowUpResponse = async (value: string) => {
    if (!followUpData) return;

    await fetch('/api/v1/follow-ups/respond', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        status_update_id: followUpData.statusUpdateId,
        response_value: value
      })
    });

    setShowFollowUp(false);
  };

  return (
    <>
      <div className="status-buttons">
        <button onClick={() => updateStatus('rolling')}>🚛 Rolling</button>
        <button onClick={() => updateStatus('waiting')}>⏱️ Waiting</button>
        <button onClick={() => updateStatus('parked')}>🅿️ Parked</button>
      </div>

      {showFollowUp && followUpData && (
        <FollowUpModal
          question={followUpData.question}
          onRespond={handleFollowUpResponse}
          onSkip={() => setShowFollowUp(false)}
        />
      )}
    </>
  );
}

function FollowUpModal({
  question,
  onRespond,
  onSkip
}: {
  question: FollowUpQuestion;
  onRespond: (value: string) => void;
  onSkip: () => void;
}) {
  return (
    <div className="modal-overlay">
      <div className="follow-up-modal">
        <h3>{question.text}</h3>
        {question.subtext && <p className="subtext">{question.subtext}</p>}

        <div className="options">
          {question.options.map((option) => (
            <button
              key={option.value}
              onClick={() => onRespond(option.value)}
              className="option-button"
            >
              <span className="emoji">{option.emoji}</span>
              <span className="label">{option.label}</span>
            </button>
          ))}
        </div>

        {question.skippable && (
          <button onClick={onSkip} className="skip-button">
            Skip
          </button>
        )}
      </div>
    </div>
  );
}
```

### CSS Example

```css
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.follow-up-modal {
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.follow-up-modal h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
  text-align: center;
}

.follow-up-modal .subtext {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin: 0 0 20px 0;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.option-button {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 16px;
}

.option-button:hover {
  border-color: #2196f3;
  background: #f5f5f5;
}

.option-button .emoji {
  font-size: 24px;
}

.option-button .label {
  font-weight: 500;
}

.skip-button {
  width: 100%;
  padding: 12px;
  border: none;
  background: transparent;
  color: #666;
  cursor: pointer;
  font-size: 14px;
}

.skip-button:hover {
  color: #333;
}
```

---

## Database Schema

All follow-up data is stored in the `status_updates` table:

```sql
CREATE TABLE status_updates (
    id UUID PRIMARY KEY,
    driver_id UUID NOT NULL,

    -- Current status
    status VARCHAR(20) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    facility_id UUID,

    -- Previous context
    prev_status VARCHAR(20),
    prev_latitude FLOAT,
    prev_longitude FLOAT,
    prev_facility_id UUID,
    prev_updated_at TIMESTAMPTZ,

    -- Calculated context
    time_since_last_seconds INT,
    distance_from_last_miles FLOAT,

    -- Follow-up question (if shown)
    follow_up_question_type VARCHAR(100),
    follow_up_question_text TEXT,
    follow_up_options JSONB,
    follow_up_skippable BOOLEAN,
    follow_up_auto_dismiss_seconds INT,

    -- Follow-up response (if answered)
    follow_up_response VARCHAR(50),
    follow_up_response_text TEXT,
    follow_up_answered_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
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

## Phase 2 Roadmap

1. **Add More Transitions**
   - ROLLING → PARKED: Ask why parking (10-hour, fuel, home time, etc.)
   - ROLLING → WAITING: Ask about load type (live, drop, detention expected?)
   - PARKED → WAITING: Did you get a load?

2. **Facility Metrics Aggregation**
   - Background job to calculate facility_metrics from status_updates
   - Public API to display facility scorecards

3. **Enhanced Context**
   - Weather conditions
   - Time of day patterns
   - Driver history patterns

4. **Smart Suggestions**
   - "Based on 47 drivers, avg wait here is 2.5 hours"
   - "93% of drivers get detention pay here"
   - "Safety rating: 4.2/5 ⭐"

---

## Summary

**Phase 1 MVP is 100% complete!** 🎉

✅ Database schema with full context tracking
✅ Pydantic models for questions and responses
✅ Intelligence engine with decision tree logic
✅ Two high-value flows (detention + parking)
✅ Status update endpoint integration
✅ Response recording endpoint
✅ History endpoint for debugging
✅ Complete API documentation

**Next Steps:**
1. Frontend integration (React modal component)
2. Test with real drivers
3. Monitor question effectiveness
4. Iterate on question copy based on feedback
5. Plan Phase 2 expansion
