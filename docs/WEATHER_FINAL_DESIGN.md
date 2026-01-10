# Weather System - Final Design

## Two Separate Systems (Simplified)

### 1. Stats Bar Weather (Always Visible)
**Purpose**: Show current conditions to all users
- **Where**: Stats bar at top of app
- **When**: Always (updates every 30 min)
- **Auth**: Not required
- **Data**: Current temperature, conditions, location
- **Good or bad**: Shows ALL weather (clear, rain, snow, etc.)

### 2. Follow-Up Alerts (Only Severe Weather)
**Purpose**: Safety alerts during status updates
- **Where**: Modal popup after status update
- **When**: Only when severe weather detected
- **Auth**: Required (part of status update)
- **Data**: Weather alert details, safety question
- **Good or bad**: Only shows ALERTS (Severe/Extreme)

---

## Example Scenarios

### Scenario 1: Clear Weather

**Driver updates status to PARKED**

```json
Response:
{
  "follow_up_question": {
    "question_type": "parking_spot_entry",
    "text": "How's the spot?",
    "options": ["Solid", "Meh", "Sketch"]
  },
  "weather_info": null  ← No alert (good weather)
}
```

**Meanwhile, stats bar shows:**
```
📍 Fresno, CA: 72°F Clear ☀️
```

**What user sees:**
1. Stats bar: "72°F Clear ☀️" (always visible)
2. Follow-up modal: "How's the spot?" (only parking question)
3. No weather alert modal (because weather is good)

---

### Scenario 2: Severe Weather

**Driver updates status to ROLLING during winter storm**

```json
Response:
{
  "follow_up_question": {
    "question_type": "detention_payment",
    "text": "Did you get detention pay?",
    "options": ["Yep", "Nope"]
  },
  "weather_info": {
    "question_type": "weather_alert",
    "text": "❄️ Winter Storm Warning",
    "subtext": "Heavy snow expected. Travel may become dangerous.",
    "options": [
      {"emoji": "👍", "label": "I'm safe", "value": "safe"},
      {"emoji": "⚠️", "label": "Pulling over", "value": "stopping"},
      {"emoji": "🏠", "label": "Already parked", "value": "parked"}
    ]
  }
}
```

**Meanwhile, stats bar shows:**
```
📍 Cheyenne, WY: 28°F Snow ❄️
```

**What user sees:**
1. Stats bar: "28°F Snow ❄️" (always visible)
2. Weather alert modal: "❄️ Winter Storm Warning - Are you safe?" (FIRST)
3. Follow-up modal: "Did you get detention pay?" (AFTER weather alert)

---

## Logic Flow

```
User updates status
    ↓
Backend checks weather alerts
    ↓
┌─────────────────────────────────────┐
│ Are there alerts?                   │
│   ↓ NO                              │
│   Return: weather_info = null       │  ← Stats bar still shows weather
│                                     │
│   ↓ YES                             │
│   Is it Severe/Extreme?             │
│     ↓ YES                           │
│     Return: weather_info = alert    │  ← Show alert modal
│                                     │
│     ↓ NO (Moderate/Minor)           │
│     Only if ROLLING status          │
│     Return: weather_info = alert    │  ← Show info modal
│     Else: weather_info = null       │  ← Stats bar only
└─────────────────────────────────────┘
```

---

## API Responses

### Normal Day (No Alerts)

```http
POST /api/v1/drivers/me/status
{
  "status": "parked",
  "latitude": 36.7594,
  "longitude": -120.0247
}

Response:
{
  "follow_up_question": {
    "question_type": "parking_spot_entry",
    "text": "How's the spot?"
  },
  "weather_info": null
}
```

Separately, stats bar fetches:
```http
GET /api/v1/map/weather?latitude=36.7594&longitude=-120.0247

Response:
{
  "available": true,
  "temperature_f": 72,
  "condition": "Clear",
  "emoji": "☀️",
  "location": "Fresno, CA"
}
```

### Severe Weather Day

```http
POST /api/v1/drivers/me/status
{
  "status": "rolling",
  "latitude": 41.3114,
  "longitude": -105.5911
}

Response:
{
  "follow_up_question": {
    "question_type": "detention_payment",
    "text": "Did you get detention pay?"
  },
  "weather_info": {
    "question_type": "weather_alert",
    "text": "❄️ Winter Storm Warning",
    "subtext": "Heavy snow expected..."
  }
}
```

Separately, stats bar fetches:
```http
GET /api/v1/map/weather?latitude=41.3114&longitude=-105.5911

Response:
{
  "available": true,
  "temperature_f": 28,
  "condition": "Snow",
  "emoji": "❄️",
  "location": "Cheyenne, WY"
}
```

---

## Frontend Implementation

### Stats Bar (Always Visible)

```typescript
function StatsBar() {
  const { weather } = useWeather();  // Fetches from /api/v1/map/weather

  return (
    <View>
      <Text>Rolling: 245 | Waiting: 89 | Parked: 312</Text>
      {weather?.available && (
        <Text>📍 {weather.location}: {weather.temperature_f}°F {weather.condition} {weather.emoji}</Text>
      )}
    </View>
  );
}
```

### Follow-Up Questions (After Status Update)

```typescript
async function updateStatus(status: string) {
  const response = await api.post('/drivers/me/status', { status, latitude, longitude });

  // Show weather alert FIRST (if present)
  if (response.weather_info) {
    await showWeatherAlertModal(response.weather_info);
  }

  // Then show primary question
  if (response.follow_up_question) {
    await showFollowUpModal(response.follow_up_question);
  }
}
```

---

## Benefits of This Approach

### ✅ Simplicity
- Stats bar = Always shows weather
- Follow-up = Only shows alerts
- Clear separation of concerns

### ✅ No Redundancy
- Don't show "Clear skies! ☀️" as a modal when it's already in stats bar
- Only interrupt driver for important weather alerts

### ✅ Data Collection
- Still collect detention/parking data even during severe weather
- Weather alerts don't block other questions

### ✅ User Experience
- Stats bar provides constant weather awareness
- Modals only appear when action needed (severe weather)
- Not annoying with repeated "good weather" messages

---

## When Weather Alerts Appear

### Severe/Extreme Weather
- **Rolling**: Always show (safety critical)
- **Waiting**: Always show (road condition check)
- **Parked**: Always show (encourage staying safe)

### Moderate Weather
- **Rolling**: Show (road condition check)
- **Waiting**: No (not urgent)
- **Parked**: No (they're already safe)

### Minor Weather / No Alerts
- **All statuses**: No modal, stats bar shows current conditions

---

## Summary

**Before**: Weather alerts replaced other follow-up questions

**Now**:
1. **Stats bar**: Always shows current weather (no auth required)
2. **Follow-up alerts**: Only shows severe weather alerts (auth required)
3. **Primary questions**: Always asked (detention, parking, facility flow)

**Result**:
- 🌤️ Everyone sees weather all the time (stats bar)
- ⚠️ Only drivers get safety alerts when needed (follow-up)
- 📊 Data collection continues uninterrupted
- 🎯 Clean, simple, purpose-driven design

---

## Files Modified (Final)

### Backend
- `app/services/weather_stats.py` - Stats bar weather service ✅
- `app/services/weather_api.py` - Weather alerts service ✅
- `app/services/follow_up_engine.py` - Alert-only logic ✅
- `app/routers/map.py` - Public `/weather` endpoint ✅
- `app/routers/drivers.py` - Returns both questions ✅
- `app/routers/locations.py` - Returns both questions ✅
- `app/models/follow_up.py` - Response model ✅

### Documentation
- `docs/WEATHER_FINAL_DESIGN.md` - This document ✅
- `docs/WEATHER_PERSISTENT_STATS.md` - Stats bar guide ✅
- `docs/WEATHER_UI_MOCKUPS.md` - Visual designs ✅

**Status**: Ready for frontend implementation! 🚀
