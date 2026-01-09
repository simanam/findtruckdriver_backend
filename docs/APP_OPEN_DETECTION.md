# App Open Detection Endpoint

## Overview

The `/api/v1/locations/app-open` endpoint implements web-first "check on app open" logic. It detects when a driver needs to update their status based on:
- Time since last update (staleness)
- Distance moved since last check-in
- Current status

## Endpoint

**POST** `/api/v1/locations/app-open`

**Authentication:** Required (Bearer token)

## Request

```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 10.0,       // Optional
  "heading": 180.0,       // Optional (0-360 degrees)
  "speed": 65.0          // Optional (mph)
}
```

## Response

```json
{
  "action": "prompt_status",           // "none" or "prompt_status"
  "reason": "welcome_back",            // "welcome_back", "location_changed", or null
  "message": "Welcome back! What's your status?",
  "current_status": "parked",
  "last_status": "parked",
  "last_location_name": "Loves #247",  // null if not at facility
  "distance_moved": 0.5,               // miles, null if first check-in
  "hours_since_update": 14.2,
  "suggested_status": null             // "rolling" if moved while parked/waiting
}
```

## Logic Flow

```
User opens app or tab regains focus
         │
         ▼
┌─────────────────────┐
│ Get current location │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ Compare to last stored location     │
│ Calculate: distance moved, time gap │
└──────────┬──────────────────────────┘
           │
           ├─────────────────────────────────────────────┐
           │                                             │
           ▼                                             ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│ 12+ hours since update  │              │ Recent + no movement    │
│ OR moved > 0.5 miles    │              │                         │
└──────────┬──────────────┘              └──────────┬──────────────┘
           │                                        │
           ▼                                        ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│ action: "prompt_status" │              │ action: "none"          │
│ Show status prompt      │              │ Silent location refresh │
└─────────────────────────┘              └─────────────────────────┘
```

## Detection Cases

### Case 1: Stale (12+ hours)

**Condition:** `hours_since_update >= 12`

**Response:**
```json
{
  "action": "prompt_status",
  "reason": "welcome_back",
  "message": "Welcome back! What's your status?",
  "suggested_status": null
}
```

**Frontend Action:** Show modal asking user to confirm/update status

---

### Case 2: Location Changed (Parked/Waiting)

**Condition:**
- `distance_moved > 0.5` miles
- `current_status` is "parked" or "waiting"

**Response:**
```json
{
  "action": "prompt_status",
  "reason": "location_changed",
  "message": "Looks like you've moved. What's your status now?",
  "distance_moved": 2.3,
  "suggested_status": "rolling"
}
```

**Frontend Action:** Show modal suggesting "rolling" status

---

### Case 3: Location Changed (Rolling)

**Condition:**
- `distance_moved > 0.5` miles
- `current_status` is "rolling"

**Response:**
```json
{
  "action": "none",
  "reason": null,
  "message": null,
  "distance_moved": 5.7
}
```

**Frontend Action:** Silent - location updated in background

---

### Case 4: No Change

**Condition:**
- `distance_moved <= 0.5` miles
- `hours_since_update < 12`

**Response:**
```json
{
  "action": "none",
  "reason": null,
  "message": null,
  "distance_moved": 0.1
}
```

**Frontend Action:** Silent - timestamp refreshed

---

## Frontend Integration

### When to Call

Call this endpoint **every time** the user opens the app or the browser tab regains focus:

```typescript
// React/Next.js example
useEffect(() => {
  const handleAppOpen = async () => {
    const location = await getCurrentLocation();

    const response = await api.locations.appOpen({
      latitude: location.latitude,
      longitude: location.longitude,
      accuracy: location.accuracy,
      heading: location.heading,
      speed: location.speed
    });

    if (response.action === "prompt_status") {
      // Show status prompt modal
      showStatusPrompt({
        reason: response.reason,
        message: response.message,
        suggestedStatus: response.suggested_status,
        currentStatus: response.current_status
      });
    }
    // If action is "none", do nothing - location was silently updated
  };

  // Call on component mount
  handleAppOpen();

  // Call on window focus
  window.addEventListener('focus', handleAppOpen);
  return () => window.removeEventListener('focus', handleAppOpen);
}, []);
```

### Status Prompt Modal

If `action === "prompt_status"`, show a modal:

```tsx
<StatusPromptModal
  isOpen={true}
  reason={response.reason}
  message={response.message}
  currentStatus={response.current_status}
  suggestedStatus={response.suggested_status}
  onConfirm={(newStatus) => {
    // Call /locations/status/update with new status
    api.locations.updateStatus(newStatus);
  }}
  onDismiss={() => {
    // User dismissed - keep current status
    // Location was already updated by app-open endpoint
  }}
/>
```

## Summary Table

| Scenario | Action | Message | Suggested Status |
|----------|--------|---------|------------------|
| **12+ hours since last update** | prompt_status | "Welcome back! What's your status?" | null |
| **Was PARKED, moved 0.5+ miles** | prompt_status | "Looks like you've moved. What's your status now?" | rolling |
| **Was WAITING, moved 0.5+ miles** | prompt_status | "Looks like you've moved. What's your status now?" | rolling |
| **Was ROLLING, moved any distance** | none | null | null |
| **Was PARKED, same location** | none | null | null |
| **Was WAITING, same location** | none | null | null |

## Benefits

1. **Web-First:** No background tracking required
2. **Privacy-Conscious:** Only checks when app is active
3. **User Control:** Always prompts, never auto-changes status
4. **Efficient:** Silent updates when no change needed
5. **Context-Aware:** Suggests appropriate status based on behavior

## Related Endpoints

- `POST /api/v1/locations/check-in` - Manual location refresh (same status)
- `POST /api/v1/locations/status/update` - Change status with location
- `GET /api/v1/locations/me` - Get current location

## Example Flows

### Flow 1: Driver Returns After 24 Hours

```
1. Driver opens app
2. Frontend calls /locations/app-open
3. Backend detects: hours_since_update = 24.5
4. Response: action="prompt_status", reason="welcome_back"
5. Frontend shows: "Welcome back! What's your status?"
6. Driver selects: "rolling"
7. Frontend calls: /locations/status/update
8. Driver is back on the map!
```

### Flow 2: Driver Moves While Parked

```
1. Driver was parked at truck stop
2. Driver leaves, drives 10 miles
3. Driver opens app
4. Frontend calls /locations/app-open
5. Backend detects: distance_moved = 10.2 miles, status="parked"
6. Response: action="prompt_status", suggested_status="rolling"
7. Frontend shows: "Looks like you've moved. Rolling now?"
8. Driver confirms "rolling"
9. Status updated, location updated, driver visible on map
```

### Flow 3: Driver Already Rolling

```
1. Driver is already rolling
2. Driver switches tabs, comes back
3. Frontend calls /locations/app-open
4. Backend detects: status="rolling", distance_moved=15 miles
5. Response: action="none"
6. Location silently updated
7. User sees map, no interruption
```

---

## Implementation Notes

- **Silent Updates:** When `action="none"`, location and `last_active` timestamp are updated automatically
- **Distance Threshold:** 0.5 miles chosen to avoid GPS drift false positives
- **Time Threshold:** 12 hours matches "stale" driver definition
- **Facility Detection:** If at a facility (within 0.1 miles), name is included in response
- **Privacy:** All returned locations are fuzzed according to driver status

---

**See [statusupdate.md](../../docs/statusupdate.md) for complete status management documentation.**
