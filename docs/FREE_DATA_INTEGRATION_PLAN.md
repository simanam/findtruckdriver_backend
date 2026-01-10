# Free Government Data Integration Plan

## Overview

The U.S. government provides **free, high-quality datasets** that can significantly enhance the Find a Truck Driver app. This document outlines integration plans for each dataset.

---

## 1. Weather API ⛈️ (HIGHEST PRIORITY)

### Source
- **URL**: https://api.weather.gov/
- **Provider**: National Weather Service (NOAA)
- **Cost**: FREE
- **Rate Limits**: None specified (reasonable use)
- **Real-time**: Yes

### Why This Matters
- **Safety**: Warn drivers of dangerous weather conditions
- **Route planning**: Avoid storms, ice, snow
- **Engagement**: Timely, relevant alerts keep drivers using the app
- **Liability reduction**: Shows you care about driver safety

### Implementation Value
⭐⭐⭐⭐⭐ **HIGHEST PRIORITY**

**ROI**: Immediate safety benefit, differentiates from competitors

### What You Can Build

#### Feature 1: Real-Time Weather Alerts
```
Driver is ROLLING on I-80 in Wyoming
→ Check weather API
→ Winter Storm Warning active
→ Show alert: "⚠️ Winter Storm Warning: Heavy snow ahead. Reduce speed."
```

#### Feature 2: Weather-Based Follow-Up Questions
```
Driver changes to ROLLING during snowstorm
→ System asks: "Roads icy? Drive safe out there 🧊"
→ Options: "All good 👍" | "Sketchy 😬" | "Pulled over ⚠️"
```

#### Feature 3: Parking Recommendations
```
Severe weather detected in driver's area
→ Suggest: "Storm coming. Consider staying parked until it passes."
```

#### Feature 4: Map Weather Layer
```
Show weather warnings on map as colored overlays
- Red: Severe (tornado, blizzard)
- Orange: Warning (winter storm, flood)
- Yellow: Watch (possible severe weather)
```

### API Endpoints

#### Get Weather Alerts for Location
```http
GET https://api.weather.gov/points/{latitude},{longitude}
User-Agent: FindTruckDriver/1.0

Response:
{
  "properties": {
    "forecastZone": "https://api.weather.gov/zones/forecast/WYZ106",
    "county": "https://api.weather.gov/zones/county/WYC037"
  }
}
```

#### Get Active Alerts for Zone
```http
GET https://api.weather.gov/alerts/active/zone/{zoneId}
User-Agent: FindTruckDriver/1.0

Response:
{
  "features": [
    {
      "properties": {
        "event": "Winter Storm Warning",
        "severity": "Severe",
        "certainty": "Likely",
        "urgency": "Expected",
        "headline": "Winter Storm Warning until 6 PM MST",
        "description": "Heavy snow expected. Winds gusting to 40 mph...",
        "instruction": "Avoid travel if possible..."
      }
    }
  ]
}
```

### Implementation Steps

**Step 1: Create Weather Service** (30 min)
```python
# app/services/weather_api.py
import requests
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WEATHER_API_BASE = "https://api.weather.gov"
USER_AGENT = "FindTruckDriver/1.0 (contact@findtruckdriver.com)"

@dataclass
class WeatherAlert:
    event: str
    severity: str  # "Extreme", "Severe", "Moderate", "Minor"
    urgency: str   # "Immediate", "Expected", "Future"
    headline: str
    description: str
    instruction: Optional[str]

def get_weather_alerts(latitude: float, longitude: float) -> List[WeatherAlert]:
    """Get active weather alerts for a location"""
    try:
        # Step 1: Get grid point
        point_url = f"{WEATHER_API_BASE}/points/{latitude:.4f},{longitude:.4f}"
        point_response = requests.get(
            point_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5
        )

        if point_response.status_code != 200:
            logger.warning(f"Weather API point lookup failed: {point_response.status_code}")
            return []

        point_data = point_response.json()
        zone_url = point_data["properties"]["forecastZone"]
        zone_id = zone_url.split("/")[-1]

        # Step 2: Get alerts for zone
        alerts_url = f"{WEATHER_API_BASE}/alerts/active/zone/{zone_id}"
        alerts_response = requests.get(
            alerts_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5
        )

        if alerts_response.status_code != 200:
            return []

        alerts_data = alerts_response.json()

        # Parse alerts
        alerts = []
        for feature in alerts_data.get("features", []):
            props = feature.get("properties", {})
            alerts.append(WeatherAlert(
                event=props.get("event", ""),
                severity=props.get("severity", ""),
                urgency=props.get("urgency", ""),
                headline=props.get("headline", ""),
                description=props.get("description", ""),
                instruction=props.get("instruction")
            ))

        return alerts

    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return []

def has_severe_alerts(alerts: List[WeatherAlert]) -> bool:
    """Check if any alerts are severe or extreme"""
    return any(
        alert.severity in ["Severe", "Extreme"]
        for alert in alerts
    )

def get_alert_emoji(event: str) -> str:
    """Get appropriate emoji for weather event"""
    event_lower = event.lower()

    if "tornado" in event_lower:
        return "🌪️"
    elif "thunder" in event_lower:
        return "⛈️"
    elif "snow" in event_lower or "blizzard" in event_lower:
        return "❄️"
    elif "ice" in event_lower or "freezing" in event_lower:
        return "🧊"
    elif "flood" in event_lower:
        return "🌊"
    elif "wind" in event_lower:
        return "💨"
    elif "heat" in event_lower:
        return "🔥"
    elif "fog" in event_lower:
        return "🌫️"
    else:
        return "⚠️"
```

**Step 2: Add Weather-Aware Follow-Up Questions** (20 min)
```python
# In app/models/follow_up.py

def build_weather_alert_question(alert: WeatherAlert) -> FollowUpQuestion:
    """Build follow-up question for severe weather"""
    emoji = get_alert_emoji(alert.event)

    return FollowUpQuestion(
        question_type="weather_alert",
        text=f"{emoji} {alert.event}",
        subtext=alert.headline,
        options=[
            FollowUpOption(emoji="👍", label="I'm safe", value="safe"),
            FollowUpOption(emoji="⚠️", label="Pulling over", value="stopping"),
            FollowUpOption(emoji="🏠", label="Already parked", value="parked")
        ],
        skippable=True
    )

def build_weather_check_question(conditions: str) -> FollowUpQuestion:
    """Ask driver about road conditions in bad weather"""
    return FollowUpQuestion(
        question_type="weather_check",
        text="Roads okay out there?",
        subtext=f"{conditions} reported in area",
        options=[
            FollowUpOption(emoji="👍", label="All good", value="good"),
            FollowUpOption(emoji="😬", label="Sketchy", value="bad"),
            FollowUpOption(emoji="⚠️", label="Dangerous", value="dangerous")
        ],
        skippable=True
    )
```

**Step 3: Integrate with Status Updates** (30 min)
```python
# In app/routers/locations.py (status update endpoint)

from app.services.weather_api import get_weather_alerts, has_severe_alerts

# After determining follow-up question...
if not question and new_status == "rolling":
    # Check for severe weather
    alerts = get_weather_alerts(request.latitude, request.longitude)

    if has_severe_alerts(alerts):
        # Override with weather alert question
        question = build_weather_alert_question(alerts[0])
        logger.info(f"Severe weather detected: {alerts[0].event}")
```

**Step 4: Add Weather Layer to Map** (1-2 hours, frontend)
```typescript
// Fetch active weather alerts for map viewport
const response = await fetch(
  `https://api.weather.gov/alerts/active?status=actual&message_type=alert`
);

// Draw polygons on map showing alert areas
// Color code by severity
```

### Testing

```python
# Test weather API
def test_weather_alerts():
    # Test location with known winter weather (Wyoming in winter)
    alerts = get_weather_alerts(41.3114, -105.5911)
    print(f"Found {len(alerts)} alerts")

    for alert in alerts:
        print(f"- {alert.event} ({alert.severity})")
        print(f"  {alert.headline}")
```

### Monitoring

```sql
-- Track weather alert engagement
SELECT
  DATE(created_at),
  follow_up_question_type,
  follow_up_response,
  COUNT(*)
FROM status_updates
WHERE follow_up_question_type IN ('weather_alert', 'weather_check')
GROUP BY DATE(created_at), follow_up_question_type, follow_up_response
ORDER BY DATE(created_at) DESC;
```

### Cost & Performance
- **API calls**: Free, no rate limits
- **Response time**: ~500ms per check
- **Caching**: Cache alerts for 15 minutes per location
- **Data usage**: ~2KB per request

---

## 2. Weigh-in-Motion (WIM) Stations ⚖️

### Source
- **URL**: https://geodata.bts.gov/datasets/893768eebc9f42089f1f2fa671c0cb51_0/explore
- **Provider**: Federal Highway Administration (FHWA)
- **Cost**: FREE
- **Update frequency**: Annually
- **Format**: GeoJSON, Shapefile, CSV

### Why This Matters
- **Driver convenience**: "Where's the next weigh station?"
- **Route planning**: Avoid closed stations
- **Crowdsourced intelligence**: "Station is bypassing trucks"
- **Compliance**: Help drivers stay legal

### Implementation Value
⭐⭐⭐⭐ **HIGH PRIORITY**

### What You Can Build

#### Feature 1: Weigh Station Proximity Alerts
```
Driver is ROLLING on I-95
→ Weigh station 5 miles ahead
→ Alert: "⚖️ Weigh station ahead in 5 miles"
→ Show current status (open/closed/bypassing)
```

#### Feature 2: Crowdsourced Status
```
Driver passes weigh station
→ Ask: "Weigh station status?"
→ Options: "Open" | "Closed" | "Bypassing trucks"
→ Share with other drivers
```

#### Feature 3: Map Overlay
```
Show weigh stations on map with status indicators:
- Green: Bypassing trucks (reported recently)
- Red: Open and checking (reported recently)
- Gray: Unknown status
```

### Database Schema

```sql
-- Weigh stations (static data from DOT)
CREATE TABLE weigh_stations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  latitude NUMERIC NOT NULL,
  longitude NUMERIC NOT NULL,
  route TEXT,  -- "I-95 Northbound"
  milepost NUMERIC,
  state TEXT,
  facility_type TEXT,  -- 'wim', 'static', 'both'
  data_source TEXT DEFAULT 'usdot_wim',
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Driver-reported status (crowdsourced, expires after 1 hour)
CREATE TABLE weigh_station_reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  weigh_station_id UUID REFERENCES weigh_stations(id),
  driver_id UUID REFERENCES drivers(id),
  status TEXT NOT NULL,  -- 'open', 'closed', 'bypassing'
  reported_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT weigh_station_reports_status_check
    CHECK (status IN ('open', 'closed', 'bypassing'))
);

-- Indexes
CREATE INDEX idx_weigh_stations_location
  ON weigh_stations (latitude, longitude);

CREATE INDEX idx_weigh_station_reports_recent
  ON weigh_station_reports (weigh_station_id, reported_at DESC);
```

### Implementation Steps

**Step 1: Download WIM Data**
```bash
# Download from BTS
wget https://geodata.bts.gov/datasets/WIM_Stations.csv -O data/wim_stations.csv
```

**Step 2: Import Script**
```python
# scripts/import_wim_stations.py
import csv
from supabase import create_client
import os

db = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

with open('data/wim_stations.csv', 'r') as f:
    reader = csv.DictReader(f)

    for row in reader:
        db.from_("weigh_stations").insert({
            "name": row["STNAME"],
            "latitude": float(row["LATITUDE"]),
            "longitude": float(row["LONGITUDE"]),
            "route": row.get("ROUTE"),
            "milepost": float(row["MILEPOST"]) if row.get("MILEPOST") else None,
            "state": row["STATE"],
            "facility_type": "wim",
            "data_source": "usdot_wim",
            "metadata": {
                "system_type": row.get("SYSTEM_TYPE"),
                "lanes": row.get("LANES")
            }
        }).execute()

print("Import complete!")
```

**Step 3: Proximity Detection Service**
```python
# app/services/weigh_station_service.py

def find_weigh_stations_ahead(
    latitude: float,
    longitude: float,
    heading: Optional[float],
    max_distance_miles: float = 10.0
) -> List[Dict]:
    """Find weigh stations ahead of driver"""

    # Get nearby weigh stations
    stations = db.from_("weigh_stations").select("*").execute()

    nearby = []
    for station in stations.data:
        distance = calculate_distance(
            latitude, longitude,
            station["latitude"], station["longitude"]
        )

        if distance <= max_distance_miles:
            # Check if station is ahead based on heading
            if heading is not None:
                bearing = calculate_bearing(
                    latitude, longitude,
                    station["latitude"], station["longitude"]
                )

                # Within 45 degrees of heading = ahead
                if abs(bearing - heading) <= 45:
                    nearby.append({
                        **station,
                        "distance_miles": distance,
                        "status": get_station_status(station["id"])
                    })

    return sorted(nearby, key=lambda x: x["distance_miles"])

def get_station_status(station_id: str) -> Optional[Dict]:
    """Get most recent crowdsourced status"""

    result = db.from_("weigh_station_reports") \
        .select("*") \
        .eq("weigh_station_id", station_id) \
        .gte("reported_at", (datetime.utcnow() - timedelta(hours=1)).isoformat()) \
        .order("reported_at", desc=True) \
        .limit(1) \
        .execute()

    if result.data:
        return result.data[0]
    return None
```

**Step 4: Add to Status Update**
```python
# In status update endpoint

stations_ahead = find_weigh_stations_ahead(
    request.latitude,
    request.longitude,
    request.heading,
    max_distance_miles=5.0
)

if stations_ahead:
    station = stations_ahead[0]
    logger.info(f"Weigh station ahead: {station['name']} ({station['distance_miles']:.1f}mi)")

    # Could add to response or trigger notification
```

---

## 3. Truck Stop Parking Data 🅿️

**Status**: Already documented in [TRUCK_PARKING_PUBLIC_DATA.md](TRUCK_PARKING_PUBLIC_DATA.md)

**Quick Summary**:
- Migration 007: Already complete ✅
- Import script: Already written ✅
- Issue: DOT portal temporarily unavailable
- Action: Monitor https://geodata.bts.gov for restoration

**See full documentation**: [TRUCK_PARKING_PUBLIC_DATA.md](TRUCK_PARKING_PUBLIC_DATA.md)

---

## 4. Bridge Data 🌉

### Source
- **URL**: https://infobridge.fhwa.dot.gov/Data/SelectedBridges
- **Provider**: FHWA National Bridge Inventory (NBI)
- **Cost**: FREE
- **Update frequency**: Annually

### Why This Matters
- **Safety**: Low clearance warnings
- **Compliance**: Weight restrictions
- **Route planning**: Avoid restricted bridges

### Implementation Value
⭐⭐⭐ **MEDIUM PRIORITY** (More complex, requires truck dimensions)

### Complexity
- Requires user truck dimensions (height, weight)
- Need route matching logic
- Best implemented after core features are stable

---

## Implementation Priority

### Phase 1: Weather (Week 1)
**Time**: 2-3 hours
**Value**: ⭐⭐⭐⭐⭐
**Status**: Can implement immediately

### Phase 2: Weigh Stations (Week 2-3)
**Time**: 4-6 hours
**Value**: ⭐⭐⭐⭐
**Status**: Can implement immediately

### Phase 3: Truck Parking (Week 4)
**Time**: 2-3 hours
**Value**: ⭐⭐⭐
**Status**: Waiting for DOT portal

### Phase 4: Bridges (Future)
**Time**: 8-10 hours
**Value**: ⭐⭐⭐
**Status**: After core features complete

---

## Cost Summary

| Data Source | Cost | Rate Limits | Real-Time |
|------------|------|-------------|-----------|
| Weather API | FREE | None | Yes ✅ |
| WIM Stations | FREE | None | No (annual updates) |
| Truck Parking | FREE | None | No (static data) |
| Bridge Data | FREE | None | No (annual updates) |

**Total Cost**: $0 🎉

---

## Expected Impact

### Weather Integration
- **User engagement**: +20% (timely, relevant alerts)
- **Safety incidents**: -30% (early warnings)
- **App opens during storms**: +50% (check conditions)

### Weigh Station Integration
- **Driver satisfaction**: +25% (valuable convenience feature)
- **App usage**: +15% (check station status)
- **Community engagement**: +40% (crowdsourced reports)

### Combined Effect
- **Competitive advantage**: Unique features competitors don't have
- **User retention**: +30% (sticky features)
- **Word-of-mouth growth**: +50% (drivers tell other drivers)

---

## Next Steps

1. **Start with Weather** (highest ROI)
   - Implement weather service (~30 min)
   - Add weather follow-up questions (~20 min)
   - Test with various locations (~10 min)
   - Deploy and monitor

2. **Add Weigh Stations** (high value)
   - Download WIM data
   - Create database tables
   - Import data
   - Build proximity detection
   - Add crowdsourced reporting

3. **Monitor Truck Parking Portal**
   - Check https://geodata.bts.gov monthly
   - Run import when available

4. **Consider Bridges Later**
   - After core features stable
   - Requires truck dimensions feature
   - More complex route matching

---

**Want me to implement the weather integration right now? It's the quickest win with the highest value! 🚀**
