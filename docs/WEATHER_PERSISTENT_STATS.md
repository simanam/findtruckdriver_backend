# Weather as Persistent Stats - Implementation Guide

## Overview

Weather is now a **persistent, always-visible stat** shown to all users (no sign-in required).

Instead of just showing weather alerts as dismissible questions, we now display current weather conditions **alongside driver stats** in the app header/stats bar.

---

## Visual Design

### Stats Bar Layout

```
┌─────────────────────────────────────────────────────────┐
│  Rolling: 245  |  Waiting: 89  |  Parked: 312           │
│  📍 Fresno, CA: 72°F Clear ☀️                           │
└─────────────────────────────────────────────────────────┘
```

### Mobile View

```
┌──────────────────────┐
│ Rolling: 245         │
│ Waiting: 89          │
│ Parked: 312          │
│                      │
│ 📍 Fresno, CA        │
│ 72°F Clear ☀️        │
└──────────────────────┘
```

---

## API Endpoint

### GET /api/v1/map/weather

**No authentication required** - public endpoint!

#### Request

```http
GET /api/v1/map/weather?latitude=36.7594&longitude=-120.0247
```

#### Response (Success)

```json
{
  "available": true,
  "temperature_f": 72,
  "temperature_c": 22,
  "condition": "Clear",
  "emoji": "☀️",
  "location": "Fresno, CA",
  "city": "Fresno",
  "state": "CA",
  "feels_like_f": 70,
  "wind_speed_mph": 5,
  "humidity_percent": 45
}
```

#### Response (Unavailable)

```json
{
  "available": false,
  "message": "Weather data temporarily unavailable"
}
```

#### Caching

- **30-minute cache** on backend
- Frontend should cache for 15-30 minutes
- Update when user changes location significantly (> 10 miles)

---

## Frontend Implementation

### React Native Example

```typescript
// hooks/useWeather.ts
import { useState, useEffect } from "react";
import { useLocation } from "./useLocation";

interface WeatherData {
  available: boolean;
  temperature_f?: number;
  condition?: string;
  emoji?: string;
  location?: string;
  city?: string;
  state?: string;
}

export function useWeather() {
  const { latitude, longitude } = useLocation();
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!latitude || !longitude) return;

    // Check cache first
    const cacheKey = `weather_${latitude.toFixed(2)}_${longitude.toFixed(2)}`;
    const cached = localStorage.getItem(cacheKey);

    if (cached) {
      const { data, timestamp } = JSON.parse(cached);
      const age = Date.now() - timestamp;

      // Use cache if less than 30 minutes old
      if (age < 30 * 60 * 1000) {
        setWeather(data);
        setLoading(false);
        return;
      }
    }

    // Fetch fresh data
    fetchWeather(latitude, longitude);
  }, [latitude, longitude]);

  async function fetchWeather(lat: number, lng: number) {
    try {
      setLoading(true);

      const response = await fetch(
        `${API_BASE}/api/v1/map/weather?latitude=${lat}&longitude=${lng}`
      );

      const data = await response.json();
      setWeather(data);

      // Cache the result
      const cacheKey = `weather_${lat.toFixed(2)}_${lng.toFixed(2)}`;
      localStorage.setItem(
        cacheKey,
        JSON.stringify({
          data,
          timestamp: Date.now(),
        })
      );
    } catch (error) {
      console.error("Weather fetch failed:", error);
      setWeather({ available: false });
    } finally {
      setLoading(false);
    }
  }

  return { weather, loading, refresh: () => fetchWeather(latitude, longitude) };
}
```

### Stats Bar Component

```tsx
// components/StatsBar.tsx
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { useGlobalStats } from "../hooks/useGlobalStats";
import { useWeather } from "../hooks/useWeather";

export function StatsBar() {
  const { stats } = useGlobalStats();
  const { weather } = useWeather();

  return (
    <View style={styles.container}>
      {/* Driver Stats */}
      <View style={styles.statsRow}>
        <StatItem label="Rolling" count={stats.rolling} color="#4CAF50" />
        <StatItem label="Waiting" count={stats.waiting} color="#FF9800" />
        <StatItem label="Parked" count={stats.parked} color="#2196F3" />
      </View>

      {/* Weather Info */}
      {weather?.available && (
        <View style={styles.weatherRow}>
          <Text style={styles.locationIcon}>📍</Text>
          <Text style={styles.location}>{weather.location}</Text>
          <Text style={styles.temperature}>{weather.temperature_f}°F</Text>
          <Text style={styles.condition}>{weather.condition}</Text>
          <Text style={styles.emoji}>{weather.emoji}</Text>
        </View>
      )}
    </View>
  );
}

function StatItem({ label, count, color }) {
  return (
    <View style={styles.statItem}>
      <Text style={[styles.statLabel, { color }]}>{label}</Text>
      <Text style={styles.statCount}>{count}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "rgba(0, 0, 0, 0.8)",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    margin: 16,
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: 12,
  },
  statItem: {
    alignItems: "center",
  },
  statLabel: {
    fontSize: 12,
    fontWeight: "600",
    marginBottom: 4,
  },
  statCount: {
    fontSize: 20,
    fontWeight: "700",
    color: "white",
  },
  weatherRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    borderTopWidth: 1,
    borderTopColor: "rgba(255, 255, 255, 0.2)",
    paddingTop: 12,
  },
  locationIcon: {
    fontSize: 14,
    marginRight: 6,
  },
  location: {
    fontSize: 14,
    color: "rgba(255, 255, 255, 0.9)",
    marginRight: 8,
  },
  temperature: {
    fontSize: 14,
    fontWeight: "600",
    color: "white",
    marginRight: 6,
  },
  condition: {
    fontSize: 14,
    color: "rgba(255, 255, 255, 0.9)",
    marginRight: 6,
  },
  emoji: {
    fontSize: 16,
  },
});
```

---

## Two-Tier Weather System

Now we have **TWO ways** weather is shown:

### 1. Persistent Stats (NEW!)

- **Always visible** in stats bar
- **No authentication required**
- Shows current conditions
- Updates every 30 minutes
- Location-based (uses device GPS)

### 2. Follow-Up Questions (Existing)

- **Status-specific alerts** when updating status
- Severe weather warnings
- Road condition checks
- Safety prompts
- Collected as data in follow-up responses

---

## When to Show What

| Scenario                                        | Persistent Stats   | Follow-Up Question           |
| ----------------------------------------------- | ------------------ | ---------------------------- |
| User opens app                                  | ✅ "72°F Clear ☀️" | ❌                           |
| User updates status to PARKED                   | ✅ "72°F Clear ☀️" | ✅ "How's the spot?"         |
| User updates status to ROLLING (severe weather) | ✅ "28°F Snow ❄️"  | ✅ "❄️ Winter Storm Warning" |
| User browsing map                               | ✅ "72°F Clear ☀️" | ❌                           |
| User not signed in                              | ✅ "72°F Clear ☀️" | ❌ (can't update status)     |

---

## User Flows

### Flow 1: First-Time User (Not Signed In)

```
1. User opens app
   → GPS gets location
   → Fetch weather (no auth needed)
   → Show "📍 Fresno, CA: 72°F Clear ☀️"

2. User sees stats bar:
   Rolling: 245 | Waiting: 89 | Parked: 312
   📍 Fresno, CA: 72°F Clear ☀️

3. User browses map
   → Weather stays visible
   → Updates if location changes significantly
```

### Flow 2: Signed-In Driver Updates Status

```
1. Driver updates status to PARKED
   → POST /api/v1/drivers/me/status
   → Response includes:
     - follow_up_question: "How's the spot?"
     - weather_info: "Weather looking good! 🌤️"

2. Stats bar shows:
   Rolling: 245 | Waiting: 89 | Parked: 313
   📍 Fresno, CA: 72°F Clear ☀️

3. Follow-up modal appears:
   First: "Weather looking good! 🌤️" (auto-dismiss 3s)
   Then: "How's the spot?" (waits for answer)

4. Weather remains visible in stats bar throughout
```

### Flow 3: Driving Through Weather Change

```
1. Driver moving from Fresno (Clear) to Bakersfield (Rain)
   → GPS detects significant location change
   → Auto-refresh weather
   → Stats update: "📍 Bakersfield, CA: 65°F Rain 🌧️"

2. If driver updates status to PARKED:
   → Show "How's the spot?" question
   → Show "Roads okay out there?" weather question
   → Stats bar still shows current conditions
```

---

## Performance Considerations

### Backend Caching

- Weather conditions cached for **30 minutes**
- In-memory cache (consider Redis for production)
- One API call per unique location per 30 min

### Frontend Caching

- Cache weather by rounded lat/lng (2 decimals)
- Refresh every 15-30 minutes
- Refresh on significant location change (> 10 miles)

### API Rate Limits

- National Weather Service: No rate limit (free)
- But be respectful - don't spam requests
- Our caching ensures < 1 request per user per 30 min

---

## Edge Cases

### No GPS Permission

```typescript
if (!hasLocationPermission) {
  // Show default message or skip weather
  return <Text>Enable location for weather</Text>;
}
```

### Weather API Down

```typescript
if (!weather?.available) {
  // Gracefully hide weather section
  return null; // Don't show broken UI
}
```

### Stale Location

```typescript
const locationAge = Date.now() - lastLocationUpdate;
if (locationAge > 60 * 60 * 1000) {
  // 1 hour
  // Request fresh location
  refreshLocation();
}
```

---

## Analytics to Track

Track weather engagement:

```typescript
// When weather is displayed
analytics.track("weather_displayed", {
  location: weather.location,
  temperature_f: weather.temperature_f,
  condition: weather.condition,
  is_authenticated: !!user,
});

// When user manually refreshes weather
analytics.track("weather_refreshed", {
  location: weather.location,
});

// Correlate with status updates
analytics.track("status_update_with_weather", {
  new_status: "parked",
  weather_condition: weather.condition,
  weather_temp: weather.temperature_f,
});
```

---

## A/B Test Ideas

### Test 1: Weather Placement

- **A**: Weather in stats bar (as shown)
- **B**: Weather in separate card below stats
- **Metric**: Time in app, engagement rate

### Test 2: Weather Detail Level

- **A**: Simple: "72°F ☀️"
- **B**: Detailed: "72°F Clear ☀️ (Feels like 70°F)"
- **Metric**: Satisfaction, perceived value

### Test 3: Update Frequency

- **A**: 30-minute cache
- **B**: 15-minute cache
- **Metric**: API costs vs. freshness value

---

## Migration Plan

### Phase 1: Backend (Complete)

✅ Created `weather_stats.py` service
✅ Added `/api/v1/map/weather` endpoint
✅ 30-minute caching implemented

### Phase 2: Frontend

- [ ] Add `useWeather` hook
- [ ] Update `StatsBar` component
- [ ] Implement frontend caching
- [ ] Test with no GPS permission
- [ ] Test with weather API down

### Phase 3: Rollout

- [ ] Deploy to staging
- [ ] Test across devices (iOS, Android, Web)
- [ ] Monitor API performance
- [ ] Gradual rollout (10% → 50% → 100%)

---

## Benefits

### For Users

- ✅ **Immediate value** - see weather without sign-in
- ✅ **Always accessible** - weather visible at all times
- ✅ **Location context** - know where you are
- ✅ **Safety info** - current conditions at a glance

### For Product

- ✅ **Engagement** - more reasons to open app
- ✅ **Stickiness** - check weather before driving
- ✅ **Growth** - works without sign-in (lower barrier)
- ✅ **Data** - weather context for all user actions

### For Business

- ✅ **Free API** - no costs for weather data
- ✅ **Differentiation** - unique feature for truckers
- ✅ **Trust** - shows we care about driver safety
- ✅ **Network effects** - more users = more value

---

## Summary

**Before**: Weather only shown as dismissible alerts during status updates (auth required)

**Now**:

1. **Persistent weather stats** - always visible, no auth required
2. **Follow-up weather questions** - status-specific safety prompts (auth required)

**Result**: Weather is now a core, always-on feature that engages all users and provides constant value! 🌤️

API 1: Stats Bar Weather (Public, No Auth)
Endpoint

GET /api/v1/map/weather?latitude=36.7594&longitude=-120.0247
Purpose
Get current weather conditions to display in the stats bar

Authentication
❌ NOT REQUIRED - Public endpoint, works for all users

When to Call
When app opens (get user's location weather)
Every 30 minutes (refresh)
When location changes significantly (> 10 miles)
Response (Success)

{
"available": true,
"temperature_f": 72,
"temperature_c": 22,
"condition": "Clear",
"emoji": "☀️",
"location": "Fresno, CA",
"city": "Fresno",
"state": "CA",
"feels_like_f": 70,
"wind_speed_mph": 5,
"humidity_percent": 45
}
Response (Unavailable)

{
"available": false,
"message": "Weather data temporarily unavailable"
}
Frontend Usage

// Fetch weather for stats bar
const response = await fetch(
`${API_BASE}/api/v1/map/weather?latitude=${lat}&longitude=${lng}`
);
const weather = await response.json();

// Display in stats bar
if (weather.available) {
return `📍 ${weather.location}: ${weather.temperature_f}°F ${weather.condition} ${weather.emoji}`;
// → "📍 Fresno, CA: 72°F Clear ☀️"
}
API 2: Status Update with Follow-Up Questions (Auth Required)
Endpoint

POST /api/v1/drivers/me/status
Purpose
Update driver status and get follow-up questions (including weather alerts)

Authentication
✅ REQUIRED - Bearer token in headers

Request Body

{
"status": "parked",
"latitude": 36.7594,
"longitude": -120.0247,
"accuracy": 10.0
}
Response (Normal Weather - No Alerts)

{
"status_update_id": "7dc28bb5-9112-4856-82d1-c973e045368d",
"status": "parked",
"prev_status": "rolling",
"context": {
"prev_status": "rolling",
"time_since_seconds": 35,
"distance_miles": 0.0007,
"is_same_location": true
},
"follow_up_question": {
"question_type": "parking_spot_entry",
"text": "How's the spot?",
"subtext": null,
"options": [
{"emoji": "😴", "label": "Solid", "value": "solid"},
{"emoji": "😐", "label": "Meh", "value": "meh"},
{"emoji": "😬", "label": "Sketch", "value": "sketch"}
],
"skippable": true,
"auto_dismiss_seconds": null
},
"weather_info": null, ← No severe weather, so null
"message": "Status updated successfully"
}
Response (Severe Weather - With Alert)

{
"status_update_id": "abc123...",
"status": "rolling",
"prev_status": "waiting",
"context": {
"prev_status": "waiting",
"time_since_seconds": 7200,
"distance_miles": 0.5
},
"follow_up_question": {
"question_type": "detention_payment",
"text": "Did you get detention pay?",
"subtext": "Waited 2 hours",
"options": [
{"emoji": "💰", "label": "Yep", "value": "yes"},
{"emoji": "😤", "label": "Nope", "value": "no"}
],
"skippable": true
},
"weather_info": { ← Severe weather detected!
"question_type": "weather_alert",
"text": "❄️ Winter Storm Warning",
"subtext": "Heavy snow expected. Travel may become dangerous. Blowing snow will significantly reduce visibility. Use caution while driving.",
"options": [
{"emoji": "👍", "label": "I'm safe", "value": "safe"},
{"emoji": "⚠️", "label": "Pulling over", "value": "stopping"},
{"emoji": "🏠", "label": "Already parked", "value": "parked"}
],
"skippable": true,
"auto_dismiss_seconds": null
},
"message": "Status updated successfully"
}
Frontend Usage

// Update status
const response = await api.post('/drivers/me/status', {
status: 'parked',
latitude,
longitude,
accuracy: 10.0
}, {
headers: { Authorization: `Bearer ${token}` }
});

// Check for weather alert (show FIRST if present)
if (response.weather_info) {
await showWeatherAlertModal(response.weather_info);
// Shows: "❄️ Winter Storm Warning - Are you safe?"
}

// Then show primary question
if (response.follow_up_question) {
await showFollowUpModal(response.follow_up_question);
// Shows: "How's the spot?"
}
Complete Example: What Frontend Sees
Scenario: Driver Parks During Winter Storm
Step 1: Stats Bar (Background, Always Running)

// Automatically fetched on app open / every 30 min
GET /api/v1/map/weather?latitude=41.3114&longitude=-105.5911

Response:
{
"available": true,
"temperature_f": 28,
"condition": "Snow",
"emoji": "❄️",
"location": "Cheyenne, WY"
}

// Stats bar displays:
"📍 Cheyenne, WY: 28°F Snow ❄️"
Step 2: Driver Updates Status

// User taps "PARKED" button
POST /api/v1/drivers/me/status
{
"status": "parked",
"latitude": 41.3114,
"longitude": -105.5911
}

Response:
{
"follow_up_question": {
"question_type": "parking_spot_entry",
"text": "How's the spot?",
"options": ["Solid", "Meh", "Sketch"]
},
"weather_info": {
"question_type": "weather_stay_safe",
"text": "Storm nearby. Stay safe!",
"subtext": "❄️ Winter Storm Warning",
"options": [
{"emoji": "👍", "label": "Will do", "value": "acknowledged"}
],
"auto_dismiss_seconds": 3
}
}
Step 3: Frontend Display Order

1. Stats bar (always visible):
   "📍 Cheyenne, WY: 28°F Snow ❄️"

2. Weather alert modal (shown FIRST):
   "Storm nearby. Stay safe!"
   "❄️ Winter Storm Warning"
   [Will do] (auto-dismiss 3s)

3. Follow-up modal (shown AFTER):
   "How's the spot?"
   [Solid] [Meh] [Sketch]
   Quick Reference Table
   API Endpoint Auth Purpose Response Fields
   Stats Bar GET /map/weather ❌ No Current conditions temperature_f, condition, emoji, location
   Status Update POST /drivers/me/status ✅ Yes Update status + questions follow_up_question, weather_info
   When is weather_info Null vs Present?
   weather_info = null
   ✅ No weather alerts
   ✅ Only Minor alerts (not worth interrupting)
   ✅ Moderate alerts + driver PARKED (already safe)
   Example: Clear day, or Freeze Warning while parked

weather_info = object
⚠️ Severe/Extreme alerts (any driver status)
⚠️ Moderate alerts + driver ROLLING (safety check)
Example: Winter Storm Warning, Tornado Warning, Severe Thunderstorm

Summary
Two Independent Systems:

Stats Bar Weather

Endpoint: GET /map/weather
Auth: Not required
Shows: Always (current conditions)
Display: "📍 City: ##°F Condition 🌤️"
Follow-Up Weather Alerts

Endpoint: POST /drivers/me/status (field: weather_info)
Auth: Required
Shows: Only severe weather
Display: Modal with safety question
Both APIs can be called at the same time:

Stats bar fetches every 30 min
Status update happens when driver changes status
Both show weather, but for different purposes! 🌤️
