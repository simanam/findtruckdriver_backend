# Location Requirements

## Overview

**Location is REQUIRED for all status updates.** The app is fundamentally location-based - drivers need to appear on the map, and all features depend on knowing where they are.

---

## Why Location is Required

### 1. **Map Visibility**
- Drivers must appear on the map for other drivers to see
- Without location, driver is invisible to the community
- Map is the core feature of the app

### 2. **Follow-Up Questions**
- All follow-up questions require location context
- Weather alerts need lat/lng
- Facility detection needs coordinates
- Distance/time calculations need previous location

### 3. **Data Quality**
- Parking spot ratings tied to location
- Detention time tracking at facilities
- Road condition reports
- All data is geo-referenced

### 4. **Safety Features**
- Weather alerts based on current location
- Severe weather warnings
- Route-specific information

---

## API Behavior

### Status Update Without Location

**Request:**
```http
POST /api/v1/drivers/me/status
{
  "status": "parked"
  // No latitude/longitude provided
}
```

**Response:**
```http
HTTP/1.1 400 Bad Request
{
  "detail": "Location is required for status updates. Please enable location permissions and try again."
}
```

### Status Update With Location

**Request:**
```http
POST /api/v1/drivers/me/status
{
  "status": "parked",
  "latitude": 36.7594,
  "longitude": -120.0247
}
```

**Response:**
```http
HTTP/1.1 200 OK
{
  "status_update_id": "...",
  "status": "parked",
  "follow_up_question": { ... },
  "weather_info": { ... },
  "message": "Status updated successfully"
}
```

---

## Frontend Handling

### User Flow

```
1. User opens app
   ↓
2. App requests location permission
   ↓
3. User response?
   ├─ ✅ Granted → Store location, enable status updates
   └─ ❌ Denied → Show location required message
```

### When Location is Denied

**Show Clear Message:**
```typescript
if (!hasLocationPermission) {
  return (
    <View style={styles.locationRequired}>
      <Icon name="map-marker-off" size={48} />
      <Text style={styles.title}>Location Required</Text>
      <Text style={styles.message}>
        FindTruckDriver needs your location to:
        • Show you on the map
        • Find nearby parking
        • Provide weather alerts
        • Connect you with other drivers
      </Text>
      <Button onPress={requestLocationPermission}>
        Enable Location
      </Button>
    </View>
  );
}
```

### Disable Status Buttons

```typescript
function StatusButtons() {
  const { hasPermission } = useLocationPermission();

  return (
    <View>
      <Button
        disabled={!hasPermission}
        onPress={() => updateStatus('rolling')}
      >
        Rolling
      </Button>
      {!hasPermission && (
        <Text style={styles.hint}>
          Enable location to update status
        </Text>
      )}
    </View>
  );
}
```

### Handle API Error

```typescript
async function updateStatus(status: string) {
  try {
    const location = await getCurrentLocation();

    if (!location) {
      throw new Error('Location unavailable');
    }

    const response = await api.post('/drivers/me/status', {
      status,
      latitude: location.latitude,
      longitude: location.longitude
    });

    return response;
  } catch (error) {
    if (error.status === 400 && error.detail.includes('Location is required')) {
      // Show location permission prompt
      Alert.alert(
        'Location Required',
        'Please enable location permissions to update your status',
        [
          { text: 'Cancel' },
          { text: 'Settings', onPress: openLocationSettings }
        ]
      );
    } else {
      // Handle other errors
      Alert.alert('Error', 'Failed to update status');
    }
  }
}
```

---

## Edge Cases

### 1. Location Permission Denied Initially

**Scenario**: User denies location on first launch

**Solution**:
- Show educational screen explaining why location is needed
- Provide button to open system settings
- Disable status update features until permission granted

### 2. Location Services Disabled

**Scenario**: User has location services off system-wide

**Solution**:
- Detect this state: `navigator.permissions.query({ name: 'geolocation' })`
- Show message: "Location services are disabled. Please enable in Settings."
- Provide deep link to system settings

### 3. Location Timeout

**Scenario**: GPS taking too long to acquire position

**Solution**:
```typescript
async function getLocationWithTimeout(timeoutMs = 10000) {
  return Promise.race([
    getCurrentPosition(),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Location timeout')), timeoutMs)
    )
  ]);
}
```

### 4. Stale Location

**Scenario**: User had location permission, but hasn't updated in hours

**Solution**:
- Check location timestamp
- If > 1 hour old, request fresh location before status update
- Fall back to cached location if fresh location fails

### 5. Low Accuracy

**Scenario**: GPS accuracy is poor (>100m)

**Solution**:
- Still allow status update (some location is better than none)
- Show warning: "Location accuracy is low. Try moving to open area."
- Backend handles fuzzing anyway for privacy

---

## Testing Checklist

### Location Permission States

- [ ] **Granted on first ask** - Status updates work immediately
- [ ] **Denied on first ask** - Show location required screen
- [ ] **Granted after denial** - Status updates work after re-enabling
- [ ] **Revoked during session** - Detect permission change, disable features
- [ ] **"Ask every time" (iOS)** - Prompt each time user updates status

### Location Accuracy

- [ ] **High accuracy (<10m)** - Works perfectly
- [ ] **Medium accuracy (10-100m)** - Works fine
- [ ] **Low accuracy (>100m)** - Works but show warning
- [ ] **No GPS (indoor)** - Use WiFi/cell tower location

### Network Conditions

- [ ] **Online with location** - Normal operation
- [ ] **Online without location** - Show error, block update
- [ ] **Offline with location** - Queue update for later (optional)
- [ ] **Offline without location** - Show error

---

## Analytics to Track

```typescript
// Track location permission state
analytics.track('location_permission_state', {
  state: 'granted' | 'denied' | 'prompt' | 'unknown',
  platform: 'ios' | 'android' | 'web'
});

// Track location errors
analytics.track('location_error', {
  error_type: 'permission_denied' | 'timeout' | 'position_unavailable',
  attempted_action: 'status_update' | 'map_load'
});

// Track location accuracy
analytics.track('location_accuracy', {
  accuracy_meters: 15.5,
  provider: 'gps' | 'network' | 'fused'
});
```

---

## User Education

### Onboarding Screen

```
┌─────────────────────────────┐
│  📍 Location Required       │
├─────────────────────────────┤
│                             │
│  FindTruckDriver is a       │
│  location-based app.        │
│                             │
│  We use your location to:   │
│                             │
│  ✓ Show you on the map      │
│  ✓ Find nearby parking      │
│  ✓ Provide weather alerts   │
│  ✓ Connect with drivers     │
│                             │
│  Your exact location is     │
│  never shared - we use      │
│  privacy fuzzing.           │
│                             │
│  [Enable Location]          │
│                             │
└─────────────────────────────┘
```

### Settings Screen

```
Location Permissions
──────────────────────
✅ Enabled
   Required for app features

Your location is used for:
• Showing you on the map
• Finding nearby facilities
• Weather alerts
• Follow-up questions

Privacy: Your exact location
is fuzzed by 0.5-1.5 miles
before being shared.

[Open System Settings]
```

---

## Privacy Considerations

Even though location is required, we protect privacy:

1. **Location Fuzzing**
   - Rolling: ±1.5 miles
   - Waiting: ±1 mile
   - Parked: ±0.5 miles

2. **Geohash**
   - 5-character precision (~3 miles)
   - Prevents exact tracking

3. **No History Sharing**
   - Only current location shown
   - Historical data not public

4. **Opt-Out Option**
   - User can still view map (read-only)
   - Just can't update their own status

---

## Summary

| Feature | Requires Location | Fallback |
|---------|------------------|----------|
| View map | ❌ No | Public data only |
| Update status | ✅ Yes | Error 400 |
| Follow-up questions | ✅ Yes | Not shown |
| Weather alerts | ✅ Yes | Not shown |
| Facility detection | ✅ Yes | Not shown |

**Bottom Line**: Location is non-negotiable for active participation. Users can view the map without location, but cannot update their status or contribute data.

This is similar to:
- Uber (can't request ride without location)
- Waze (can't navigate without location)
- Yelp (can search without location, but "near me" requires it)

For FindTruckDriver, the entire value proposition is "see where drivers are" - so location is fundamental to the experience.
