# Map Implementation Guide - Complete Frontend Logic

## Overview

The map should show:
1. **YOU (current user)** - Always visible as a special marker (blue dot)
2. **Other drivers** - Show as individuals OR clusters depending on count

## The Correct Logic

### Step 1: Always Load "Me" First

```typescript
async function loadMyLocation(token: string) {
  try {
    const response = await fetch('/api/v1/locations/me', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      if (response.status === 404) {
        // User hasn't checked in yet - show prompt
        showCheckInPrompt();
        return null;
      }
      throw new Error('Failed to load location');
    }

    const data = await response.json();

    // Response format:
    // {
    //   "driver_id": "uuid",
    //   "handle": "steel_hawk",
    //   "status": "waiting",
    //   "latitude": 36.8339,
    //   "longitude": -119.9089,
    //   "facility_name": "Pilot Travel Center #456" or null,
    //   "updated_at": "2026-01-09T15:29:39.651619+00:00"
    // }

    return data;
  } catch (error) {
    console.error('Failed to load my location:', error);
    return null;
  }
}
```

### Step 2: Show "YOU" Marker

```typescript
function addMyMarker(myLocation: MyLocationResponse, map: MapInstance) {
  if (!myLocation) return;

  // Create special "ME" marker
  const marker = new Marker({
    position: {
      lat: myLocation.latitude,
      lng: myLocation.longitude
    },
    map: map,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: '#4285F4', // Google blue
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeWeight: 3,
      scale: 12,
    },
    zIndex: 1000, // Always on top
    title: 'YOU',
    animation: google.maps.Animation.DROP
  });

  // Add pulsing animation
  addPulsingEffect(marker);

  // Show info window on click
  marker.addListener('click', () => {
    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 8px;">
          <h3 style="margin: 0 0 8px 0; color: #4285F4;">📍 You</h3>
          <p style="margin: 4px 0;"><strong>Handle:</strong> ${myLocation.handle}</p>
          <p style="margin: 4px 0;"><strong>Status:</strong> ${getStatusEmoji(myLocation.status)} ${myLocation.status}</p>
          ${myLocation.facility_name ? `<p style="margin: 4px 0;"><strong>Near:</strong> ${myLocation.facility_name}</p>` : ''}
          <p style="margin: 4px 0; font-size: 12px; color: #666;">
            Updated: ${formatTimeAgo(myLocation.updated_at)}
          </p>
        </div>
      `
    });
    infoWindow.open(map, marker);
  });

  // Center map on user's location
  map.setCenter({lat: myLocation.latitude, lng: myLocation.longitude});
  map.setZoom(10);

  return marker;
}
```

### Step 3: Load Other Drivers

```typescript
async function loadOtherDrivers(
  myDriverId: string,
  mapCenter: {lat: number, lng: number},
  radiusMiles: number
) {
  const response = await fetch(
    `/api/v1/map/drivers?latitude=${mapCenter.lat}&longitude=${mapCenter.lng}&radius_miles=${radiusMiles}`
  );

  const data = await response.json();

  // Filter out self (backend might include you)
  const otherDrivers = data.drivers.filter(
    (d: any) => d.driver_id !== myDriverId
  );

  return otherDrivers;
}
```

### Step 4: Decide Clusters vs Individuals

```typescript
async function loadMapDrivers(
  token: string,
  map: MapInstance,
  mapCenter: {lat: number, lng: number},
  radiusMiles: number
) {
  // 1️⃣ Load and show "ME" marker
  const myLocation = await loadMyLocation(token);
  let myMarker = null;

  if (myLocation) {
    myMarker = addMyMarker(myLocation, map);
  }

  // 2️⃣ Load other drivers
  const otherDrivers = await loadOtherDrivers(
    myLocation?.driver_id,
    mapCenter,
    radiusMiles
  );

  // 3️⃣ Decide: show individuals or clusters?
  const CLUSTER_THRESHOLD = 10; // Cluster if more than 10 drivers

  if (otherDrivers.length < CLUSTER_THRESHOLD) {
    // Show individual markers
    otherDrivers.forEach((driver: any) => {
      addDriverMarker(driver, map);
    });
  } else {
    // Show clusters
    const clustersResponse = await fetch(
      `/api/v1/map/clusters?latitude=${mapCenter.lat}&longitude=${mapCenter.lng}&radius_miles=${radiusMiles}&min_drivers=2`
    );
    const clusters = await clustersResponse.json();

    clusters.clusters.forEach((cluster: any) => {
      addClusterMarker(cluster, map);
    });
  }

  return {
    myMarker,
    otherDriverCount: otherDrivers.length
  };
}
```

### Step 5: Add Driver Markers (Individual)

```typescript
function addDriverMarker(driver: any, map: MapInstance) {
  const statusColors = {
    rolling: '#10B981', // Green
    waiting: '#F59E0B', // Orange
    parked: '#EF4444'   // Red
  };

  const marker = new Marker({
    position: {
      lat: driver.latitude,
      lng: driver.longitude
    },
    map: map,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: statusColors[driver.status] || '#6B7280',
      fillOpacity: 0.8,
      strokeColor: '#ffffff',
      strokeWeight: 2,
      scale: 8,
    },
    zIndex: 100,
    title: driver.handle
  });

  // Info window
  marker.addListener('click', () => {
    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 8px;">
          <h3 style="margin: 0 0 8px 0;">${driver.handle}</h3>
          <p style="margin: 4px 0;">
            <strong>Status:</strong> ${getStatusEmoji(driver.status)} ${driver.status}
          </p>
          <p style="margin: 4px 0;">
            <strong>Distance:</strong> ${driver.distance_miles} miles away
          </p>
          <p style="margin: 4px 0; font-size: 12px; color: #666;">
            Active: ${formatTimeAgo(driver.last_active)}
          </p>
        </div>
      `
    });
    infoWindow.open(map, marker);
  });

  return marker;
}
```

### Step 6: Add Cluster Markers (Grouped)

```typescript
function addClusterMarker(cluster: any, map: MapInstance) {
  const marker = new Marker({
    position: {
      lat: cluster.center.latitude,
      lng: cluster.center.longitude
    },
    map: map,
    label: {
      text: cluster.total_drivers.toString(),
      color: 'white',
      fontSize: '14px',
      fontWeight: 'bold'
    },
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: '#6366F1', // Indigo
      fillOpacity: 0.8,
      strokeColor: '#ffffff',
      strokeWeight: 3,
      scale: 15,
    },
    zIndex: 50
  });

  // Click to zoom into cluster
  marker.addListener('click', () => {
    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 8px;">
          <h3 style="margin: 0 0 8px 0;">Driver Cluster</h3>
          <p style="margin: 4px 0;"><strong>Total drivers:</strong> ${cluster.total_drivers}</p>
          <p style="margin: 4px 0;"><strong>Breakdown:</strong></p>
          <ul style="margin: 4px 0; padding-left: 20px;">
            ${Object.entries(cluster.status_breakdown).map(([status, count]) =>
              `<li>${getStatusEmoji(status)} ${status}: ${count}</li>`
            ).join('')}
          </ul>
          <button onclick="zoomToCluster(${cluster.center.latitude}, ${cluster.center.longitude})">
            Zoom In
          </button>
        </div>
      `
    });
    infoWindow.open(map, marker);
  });

  return marker;
}
```

---

## Complete Example

```typescript
import { useEffect, useState } from 'react';
import { GoogleMap, useLoadScript } from '@react-google-maps/api';

function MapView() {
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY
  });

  const [map, setMap] = useState(null);
  const [myLocation, setMyLocation] = useState(null);
  const [markers, setMarkers] = useState([]);

  useEffect(() => {
    if (!map) return;

    loadMap();
  }, [map]);

  async function loadMap() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Clear existing markers
    markers.forEach(m => m.setMap(null));
    setMarkers([]);

    // Get map center and radius
    const center = map.getCenter();
    const bounds = map.getBounds();
    const ne = bounds.getNorthEast();
    const radiusMiles = calculateDistance(
      center.lat(), center.lng(),
      ne.lat(), ne.lng()
    );

    // Load all map data
    const result = await loadMapDrivers(
      token,
      map,
      {lat: center.lat(), lng: center.lng()},
      radiusMiles
    );

    setMyLocation(result.myMarker);
  }

  // Reload when map moves/zooms
  function handleMapChange() {
    loadMap();
  }

  if (!isLoaded) return <div>Loading map...</div>;

  return (
    <GoogleMap
      mapContainerStyle={{ width: '100%', height: '100vh' }}
      center={{ lat: 39.8283, lng: -98.5795 }} // USA center
      zoom={4}
      onLoad={setMap}
      onDragEnd={handleMapChange}
      onZoomChanged={handleMapChange}
      options={{
        styles: mapStyles, // Your custom map styling
        mapTypeControl: false,
        fullscreenControl: true,
        streetViewControl: false
      }}
    >
      {/* Markers are added via loadMapDrivers() */}
    </GoogleMap>
  );
}
```

---

## Helper Functions

```typescript
function getStatusEmoji(status: string): string {
  const emojis = {
    rolling: '🚛',
    waiting: '⏳',
    parked: '🅿️'
  };
  return emojis[status] || '📍';
}

function formatTimeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 3959; // Earth radius in miles
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}
```

---

## API Endpoints Summary

### 1. Get My Location (Always call this first)
```
GET /api/v1/locations/me
Authorization: Bearer {token}

Response:
{
  "driver_id": "uuid",
  "handle": "steel_hawk",
  "status": "waiting",
  "latitude": 36.8339,
  "longitude": -119.9089,
  "facility_name": "Pilot Travel Center #456",
  "updated_at": "2026-01-09T15:29:39+00:00"
}
```

### 2. Get Other Drivers (Individual markers)
```
GET /api/v1/map/drivers?latitude=36.83&longitude=-119.91&radius_miles=50

Response:
{
  "count": 5,
  "drivers": [
    {
      "driver_id": "uuid",
      "handle": "road_warrior",
      "status": "rolling",
      "latitude": 36.85,
      "longitude": -119.95,
      "distance_miles": 2.5,
      "last_active": "2026-01-09T15:30:00+00:00"
    }
  ]
}
```

### 3. Get Clusters (When many drivers)
```
GET /api/v1/map/clusters?latitude=36.83&longitude=-119.91&radius_miles=50&min_drivers=2

Response:
{
  "cluster_count": 3,
  "clusters": [
    {
      "geohash": "9qd9",
      "center": {"latitude": 36.85, "longitude": -119.92},
      "total_drivers": 5,
      "status_breakdown": {"rolling": 2, "waiting": 2, "parked": 1}
    }
  ]
}
```

---

## Testing

1. **Test with 1 driver (you):**
   - Should show blue "YOU" marker
   - Map centered on your location
   - No other markers

2. **Test with 2-9 drivers:**
   - Should show blue "YOU" marker
   - Individual colored markers for others
   - Different colors by status

3. **Test with 10+ drivers:**
   - Should show blue "YOU" marker
   - Cluster markers for groups
   - Click cluster to see breakdown

---

## Troubleshooting

### "I can't see myself on map"
- ✅ Call `/api/v1/locations/me` endpoint
- ✅ Check response status (404 means not checked in yet)
- ✅ Add blue marker at response coordinates
- ✅ Center map on your location

### "No drivers showing"
- ✅ Check you're calling `/api/v1/map/drivers` (not `/clusters`)
- ✅ Verify radius_miles covers your area
- ✅ Filter out your own driver_id from results

### "Clusters show 0 drivers"
- ✅ Clusters need `min_drivers >= 2`
- ✅ Use `/api/v1/map/drivers` for individual view
- ✅ Only use clusters when 10+ drivers exist

---

## Next Steps

1. Implement the map loading logic above
2. Test with your current single driver
3. Add a few test drivers to verify clustering
4. Add real-time updates (WebSocket or polling)
5. Add map controls (filter by status, search, etc.)
