# Frontend Quick Start Guide

## 🎯 Backend Server Info

- **Base URL:** `http://localhost:8000`
- **All endpoints start with:** `/api/v1/`
- **API Documentation:** http://localhost:8000/docs (when server is running)

---

## 🔑 Authentication - Email OTP (Passwordless)

### 1. Request OTP Code

**Endpoint:** `POST /api/v1/auth/email/otp/request`

**Request:**
```json
{
  "email": "driver@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Verification code sent to driver@example.com",
  "email": "driver@example.com"
}
```

**Frontend Code:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/auth/email/otp/request', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'driver@example.com' })
});
const data = await response.json();
```

---

### 2. Verify OTP Code

**Endpoint:** `POST /api/v1/auth/email/otp/verify`

**Request:**
```json
{
  "email": "driver@example.com",
  "code": "12345678"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid-here",
    "email": "driver@example.com",
    "phone": null,
    "created_at": "2024-01-08T12:00:00Z"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "refresh-token-here",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "driver": null
}
```

**Frontend Code:**
```typescript
const response = await fetch('http://localhost:8000/api/v1/auth/email/otp/verify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'driver@example.com',
    code: '12345678'
  })
});
const data = await response.json();

// Save tokens
await AsyncStorage.setItem('access_token', data.tokens.access_token);
await AsyncStorage.setItem('refresh_token', data.tokens.refresh_token);

// Check if user has profile
if (data.driver) {
  // Navigate to Home
} else {
  // Navigate to Onboarding
}
```

---

## 👤 Driver Profile

### 3. Create Driver Profile (Onboarding)

**Endpoint:** `POST /api/v1/drivers`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
  "handle": "trucker_mike",
  "avatar_id": "avatar_001",
  "status": "parked"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "user_id": "uuid-here",
  "handle": "trucker_mike",
  "avatar_id": "avatar_001",
  "status": "parked",
  "created_at": "2024-01-08T12:00:00Z",
  "updated_at": "2024-01-08T12:00:00Z"
}
```

**Frontend Code:**
```typescript
const token = await AsyncStorage.getItem('access_token');

const response = await fetch('http://localhost:8000/api/v1/drivers', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    handle: 'trucker_mike',
    avatar_id: 'avatar_001',
    status: 'parked'
  })
});
const data = await response.json();
```

---

### 4. Get My Profile

**Endpoint:** `GET /api/v1/drivers/me`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response:**
```json
{
  "id": "uuid-here",
  "user_id": "uuid-here",
  "handle": "trucker_mike",
  "avatar_id": "avatar_001",
  "status": "rolling",
  "created_at": "2024-01-08T12:00:00Z",
  "updated_at": "2024-01-08T12:00:00Z"
}
```

**Frontend Code:**
```typescript
const token = await AsyncStorage.getItem('access_token');

const response = await fetch('http://localhost:8000/api/v1/drivers/me', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const data = await response.json();
```

---

## 📍 Location & Status

### 5. Check In (Refresh Location, Same Status)

**Endpoint:** `POST /api/v1/locations/check-in`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
  "latitude": 34.0522,
  "longitude": -118.2437,
  "accuracy": 10.0
}
```

**Response:**
```json
{
  "success": true,
  "status": "rolling",
  "location": {
    "latitude": 34.053,
    "longitude": -118.244,
    "facility_name": null,
    "updated_at": "2024-01-08T12:30:00Z"
  },
  "message": "Location updated. Status: rolling"
}
```

**Frontend Code:**
```typescript
const token = await AsyncStorage.getItem('access_token');
const { latitude, longitude, accuracy } = await getLocationAsync();

const response = await fetch('http://localhost:8000/api/v1/locations/check-in', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    latitude,
    longitude,
    accuracy
  })
});
const data = await response.json();
```

---

### 6. Update Status with Location

**Endpoint:** `POST /api/v1/locations/status/update`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
  "status": "waiting",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "accuracy": 10.0
}
```

**Response:**
```json
{
  "success": true,
  "old_status": "rolling",
  "new_status": "waiting",
  "location": {
    "latitude": 34.053,
    "longitude": -118.244,
    "facility_name": "Truck Stop XYZ",
    "updated_at": "2024-01-08T12:30:00Z"
  },
  "wait_context": {
    "others_waiting": 12,
    "avg_wait_hours": 2.5
  },
  "message": "Status changed from rolling to waiting"
}
```

**Frontend Code:**
```typescript
const token = await AsyncStorage.getItem('access_token');
const { latitude, longitude, accuracy } = await getLocationAsync();

const response = await fetch('http://localhost:8000/api/v1/locations/status/update', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    status: 'waiting',  // 'rolling', 'waiting', or 'parked'
    latitude,
    longitude,
    accuracy
  })
});
const data = await response.json();

if (data.wait_context) {
  console.log(`${data.wait_context.others_waiting} others waiting here`);
  console.log(`Average wait: ${data.wait_context.avg_wait_hours} hours`);
}
```

---

### 7. Find Nearby Drivers

**Endpoint:** `GET /api/v1/locations/nearby`

**Query Parameters:**
- `latitude` (required): User's latitude
- `longitude` (required): User's longitude
- `radius_miles` (optional, default: 25): Search radius in miles
- `status_filter` (optional): Filter by status ('rolling', 'waiting', 'parked')
- `limit` (optional, default: 100): Max results

**Example URL:**
```
http://localhost:8000/api/v1/locations/nearby?latitude=34.0522&longitude=-118.2437&radius_miles=10&status_filter=waiting
```

**Response:**
```json
{
  "drivers": [
    {
      "driver_id": "uuid-here",
      "handle": "trucker_mike",
      "avatar_id": "avatar_001",
      "status": "waiting",
      "location": {
        "latitude": 34.053,
        "longitude": -118.244,
        "facility_name": "Truck Stop XYZ",
        "updated_at": "2024-01-08T12:00:00Z"
      },
      "distance_miles": 2.3
    }
  ],
  "total": 1,
  "search_center": {
    "latitude": 34.0522,
    "longitude": -118.2437
  },
  "radius_miles": 10
}
```

**Frontend Code:**
```typescript
const { latitude, longitude } = await getLocationAsync();

const url = new URL('http://localhost:8000/api/v1/locations/nearby');
url.searchParams.append('latitude', latitude.toString());
url.searchParams.append('longitude', longitude.toString());
url.searchParams.append('radius_miles', '10');
url.searchParams.append('status_filter', 'waiting');

const response = await fetch(url.toString());
const data = await response.json();

// Display drivers on map
data.drivers.forEach(driver => {
  console.log(`${driver.handle} is ${driver.distance_miles} miles away`);
});
```

---

## 🗺️ Map Features

### 8. Get Drivers in Map Area

**Endpoint:** `GET /api/v1/map/drivers`

**Query Parameters:**
- `latitude` (required)
- `longitude` (required)
- `radius_miles` (optional, default: 25)
- `status_filter` (optional)
- `limit` (optional, default: 100)

**Frontend Code:**
```typescript
const response = await fetch(
  `http://localhost:8000/api/v1/map/drivers?latitude=34.0522&longitude=-118.2437&radius_miles=50`
);
const data = await response.json();
```

---

### 9. Get Map Statistics

**Endpoint:** `GET /api/v1/map/stats`

**Query Parameters:**
- `latitude` (required)
- `longitude` (required)
- `radius_miles` (optional, default: 50)

**Response:**
```json
{
  "area": {
    "center": {
      "latitude": 34.0522,
      "longitude": -118.2437
    },
    "radius_miles": 50
  },
  "stats": {
    "total_drivers": 125,
    "rolling": 45,
    "waiting": 60,
    "parked": 20,
    "active_last_hour": 80,
    "hotspots": 3
  }
}
```

**Frontend Code:**
```typescript
const response = await fetch(
  `http://localhost:8000/api/v1/map/stats?latitude=34.0522&longitude=-118.2437&radius_miles=50`
);
const data = await response.json();

console.log(`Total drivers: ${data.stats.total_drivers}`);
console.log(`Waiting: ${data.stats.waiting}`);
```

---

## 🔄 Token Refresh

### 10. Refresh Access Token

**Endpoint:** `POST /api/v1/auth/token/refresh`

**Request:**
```json
{
  "refresh_token": "your-refresh-token"
}
```

**Response:**
```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Frontend Code:**
```typescript
const refreshToken = await AsyncStorage.getItem('refresh_token');

const response = await fetch('http://localhost:8000/api/v1/auth/token/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token: refreshToken })
});

if (response.ok) {
  const data = await response.json();
  await AsyncStorage.setItem('access_token', data.access_token);
  await AsyncStorage.setItem('refresh_token', data.refresh_token);
}
```

---

## 📱 Complete React Native Example

### services/auth.ts

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = 'http://localhost:8000/api/v1';

export const AuthService = {
  // 1. Request OTP
  async requestEmailOTP(email: string): Promise<void> {
    const response = await fetch(`${API_BASE}/auth/email/otp/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send OTP');
    }
  },

  // 2. Verify OTP
  async verifyEmailOTP(email: string, code: string) {
    const response = await fetch(`${API_BASE}/auth/email/otp/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Invalid code');
    }

    const data = await response.json();

    // Save tokens
    await AsyncStorage.setItem('access_token', data.tokens.access_token);
    await AsyncStorage.setItem('refresh_token', data.tokens.refresh_token);

    return data;
  },

  // 3. Get current user profile
  async getMyProfile() {
    const token = await AsyncStorage.getItem('access_token');

    const response = await fetch(`${API_BASE}/drivers/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return null; // No profile yet
      }
      throw new Error('Failed to get profile');
    }

    return await response.json();
  },

  // 4. Create profile
  async createProfile(handle: string, avatarId: string, status: string) {
    const token = await AsyncStorage.getItem('access_token');

    const response = await fetch(`${API_BASE}/drivers`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        handle,
        avatar_id: avatarId,
        status,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create profile');
    }

    return await response.json();
  },
};
```

---

## 🧪 Testing with curl

```bash
# 1. Request OTP
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com"}'

# 2. Check your email for the 8-digit code

# 3. Verify OTP
curl -X POST http://localhost:8000/api/v1/auth/email/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com", "code": "12345678"}'

# 4. Save the access_token from the response

# 5. Get profile
curl http://localhost:8000/api/v1/drivers/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 6. Create profile
curl -X POST http://localhost:8000/api/v1/drivers \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "handle": "trucker_mike",
    "avatar_id": "avatar_001",
    "status": "parked"
  }'
```

---

## ⚠️ Common Issues

### Issue: 404 Not Found

**Problem:** Frontend calling `/auth/email/otp/request` instead of `/api/v1/auth/email/otp/request`

**Solution:** Always include `/api/v1/` prefix in all API calls

### Issue: 401 Unauthorized

**Problem:** Missing or expired access token

**Solution:**
1. Check token exists: `await AsyncStorage.getItem('access_token')`
2. Include in header: `Authorization: Bearer ${token}`
3. Refresh token if expired

### Issue: CORS Error (Web only)

**Problem:** Browser blocking cross-origin requests

**Solution:** Backend already configured for CORS. Make sure you're using correct URL.

### Issue: Network Error on Device

**Problem:** Using `localhost` on physical device

**Solution:** Use your computer's IP address:
```typescript
const API_URL = 'http://192.168.1.XXX:8000';  // Replace XXX with your IP
```

Find your IP:
- Mac: `ipconfig getifaddr en0`
- Windows: `ipconfig` (look for IPv4 Address)

---

## 📚 Complete Endpoint Reference

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/v1/auth/email/otp/request` | No | Request email OTP code |
| POST | `/api/v1/auth/email/otp/verify` | No | Verify email OTP code |
| POST | `/api/v1/auth/token/refresh` | No | Refresh access token |
| POST | `/api/v1/auth/logout` | Yes | Logout user |
| POST | `/api/v1/drivers` | Yes | Create driver profile |
| GET | `/api/v1/drivers/me` | Yes | Get my profile |
| PATCH | `/api/v1/drivers/me` | Yes | Update my profile |
| PATCH | `/api/v1/drivers/me/status` | Yes | Update status only |
| POST | `/api/v1/locations/check-in` | Yes | Check in (refresh location) |
| POST | `/api/v1/locations/status/update` | Yes | Update status + location |
| GET | `/api/v1/locations/me` | Yes | Get my current location |
| GET | `/api/v1/locations/nearby` | No | Find nearby drivers |
| GET | `/api/v1/map/drivers` | No | Get drivers in map area |
| GET | `/api/v1/map/clusters` | No | Get driver clusters |
| GET | `/api/v1/map/hotspots` | No | Get hotspot locations |
| GET | `/api/v1/map/stats` | No | Get map statistics |

---

## 🚀 Ready to Start!

1. **Make sure backend is running:** `cd finddriverbackend && ./run_dev.sh`
2. **Test with curl** to verify endpoints work
3. **Update your frontend** `config/api.ts` with correct URLs
4. **Implement authentication** using the code examples above
5. **Build onboarding** and location features

**Need help?** Check http://localhost:8000/docs for interactive API documentation!
