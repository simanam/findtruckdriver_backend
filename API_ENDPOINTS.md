# Find a Truck Driver - API Endpoints

## Summary

✅ **Phase 1 Complete:** Authentication & Driver Profile endpoints implemented and working!

### What's Working
- Supabase database connection with new API keys (`sb_publishable_`, `sb_secret_`)
- FastAPI server running on http://localhost:8000
- Interactive API docs at http://localhost:8000/docs
- Authentication system (OTP, Magic Link)
- Driver profile management

---

## Implemented Endpoints

### 🔐 Authentication (`/api/v1/auth`)

#### 1. Request Email OTP (Recommended - Free!)
```http
POST /api/v1/auth/email/otp/request
Content-Type: application/json

{
  "email": "driver@example.com"
}
```
**Returns:** Success message (code sent to email)

#### 2. Verify Email OTP
```http
POST /api/v1/auth/email/otp/verify
Content-Type: application/json

{
  "email": "driver@example.com",
  "code": "123456"
}
```
**Returns:** User info, access token, refresh token, and driver profile (if exists)
**No password required!** ✨

#### 3. Request Phone OTP (SMS - Costs Money)
```http
POST /api/v1/auth/otp/request
Content-Type: application/json

{
  "phone": "+14155551234"
}
```

#### 4. Verify Phone OTP
```http
POST /api/v1/auth/otp/verify
Content-Type: application/json

{
  "phone": "+14155551234",
  "code": "123456"
}
```
**Returns:** User info, access token, refresh token, and driver profile (if exists)

#### 5. Request Magic Link via Email (Alternative)
```http
POST /api/v1/auth/magic-link/request
Content-Type: application/json

{
  "email": "driver@example.com"
}
```

#### 6. Refresh Access Token
```http
POST /api/v1/auth/token/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token"
}
```

#### 7. Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

#### 8. Get Current User Info
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

---

### 👤 Driver Profile (`/api/v1/drivers`)

#### 1. Create Driver Profile (Onboarding)
```http
POST /api/v1/drivers
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "handle": "trucker_mike",
  "avatar_id": "avatar_123",
  "status": "parked"
}
```

#### 2. Get My Profile
```http
GET /api/v1/drivers/me
Authorization: Bearer <access_token>
```

#### 3. Update My Profile
```http
PUT /api/v1/drivers/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "handle": "new_handle",
  "avatar_id": "new_avatar"
}
```

#### 4. Update My Status
```http
POST /api/v1/drivers/me/status
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "rolling"
}
```
**Valid statuses:** `rolling`, `waiting`, `parked`

#### 5. Get Driver by ID (Public)
```http
GET /api/v1/drivers/{driver_id}
```
Returns limited public information

#### 6. Get Driver by Handle (Public)
```http
GET /api/v1/drivers/handle/{handle}
```
Returns limited public information

---

## Health & Info Endpoints

### Health Check
```http
GET /health
```

### API Info
```http
GET /
```

---

---

### 📍 Location & Check-in (`/api/v1/locations`)

#### 1. Manual Check-In
```http
POST /api/v1/locations/check-in
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "latitude": 34.0522,
  "longitude": -118.2437,
  "accuracy": 10.0,
  "heading": 45.0,
  "speed": 0.0
}
```
**Returns:** Confirmation with fuzzed location, facility name (if at one), current status

#### 2. Update Status with Location
```http
POST /api/v1/locations/status/update
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "waiting",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "accuracy": 10.0,
  "heading": 0.0,
  "speed": 0.0
}
```
**Returns:** Status change confirmation, location, wait context (if waiting at facility)

#### 3. Get My Location
```http
GET /api/v1/locations/me
Authorization: Bearer <access_token>
```
**Returns:** Current fuzzed location

#### 4. Find Nearby Drivers (Public)
```http
GET /api/v1/locations/nearby?latitude=34.0522&longitude=-118.2437&radius_miles=10&status_filter=waiting
```
**Query Params:**
- `latitude` (required) - Center latitude
- `longitude` (required) - Center longitude
- `radius_miles` (optional, default: 10) - Search radius
- `status_filter` (optional) - Filter by status: rolling, waiting, parked

**Returns:** List of nearby drivers with fuzzed locations

---

---

### 🗺️ Map & Search (`/api/v1/map`)

#### 1. Get Drivers in Map Area
```http
GET /api/v1/map/drivers?latitude=34.0522&longitude=-118.2437&radius_miles=25&status_filter=waiting&limit=100
```
**Query Params:**
- `latitude` (required) - Center latitude
- `longitude` (required) - Center longitude
- `radius_miles` (optional, default: 25) - Search radius (1-100 miles)
- `status_filter` (optional) - Filter by status
- `limit` (optional, default: 100) - Max drivers to return (1-500)

**Returns:** All drivers in the area with fuzzed locations

#### 2. Get Driver Clusters
```http
GET /api/v1/map/clusters?latitude=34.0522&longitude=-118.2437&radius_miles=50&min_drivers=3
```
**Query Params:**
- `latitude` (required) - Center latitude
- `longitude` (required) - Center longitude
- `radius_miles` (optional, default: 50) - Search radius (1-200 miles)
- `min_drivers` (optional, default: 3) - Minimum drivers per cluster (2-20)

**Returns:** Aggregated clusters with status breakdown

#### 3. Get Hotspots (High Wait Times)
```http
GET /api/v1/map/hotspots?latitude=34.0522&longitude=-118.2437&radius_miles=100&min_waiting_drivers=10
```
**Query Params:**
- `latitude` (required) - Center latitude
- `longitude` (required) - Center longitude
- `radius_miles` (optional, default: 100) - Search radius (1-300 miles)
- `min_waiting_drivers` (optional, from config) - Min waiting drivers to be a hotspot

**Returns:** Busy facilities with many waiting drivers, average wait times

#### 4. Get Map Statistics
```http
GET /api/v1/map/stats?latitude=34.0522&longitude=-118.2437&radius_miles=50
```
**Query Params:**
- `latitude` (required) - Center latitude
- `longitude` (required) - Center longitude
- `radius_miles` (optional, default: 50) - Search radius (1-200 miles)

**Returns:** Aggregated stats (total drivers, status breakdown, activity %)

---

## Next Steps (Optional Future Features)

### 📊 Advanced Analytics
- [ ] `GET /api/v1/status/history` - Get status change history
- [ ] `GET /api/v1/stats/me` - Personal statistics dashboard
- [ ] `GET /api/v1/stats/trends` - Historical trends

### 🏢 Facilities Management
- [ ] `GET /api/v1/facilities` - List all facilities
- [ ] `GET /api/v1/facilities/{id}` - Get facility details
- [ ] `GET /api/v1/facilities/{id}/stats` - Facility statistics

---

## Authentication Flow

### For Phone Authentication:
1. User enters phone number
2. `POST /api/v1/auth/otp/request` → Receives SMS with code
3. User enters code
4. `POST /api/v1/auth/otp/verify` → Receives tokens + user info
5. If no driver profile: `POST /api/v1/drivers` (onboarding)
6. Use access token in `Authorization: Bearer <token>` header for all protected endpoints

### For Email Authentication:
1. User enters email
2. `POST /api/v1/auth/magic-link/request` → Receives email with link
3. User clicks link in email
4. Frontend handles callback with tokens
5. Same onboarding flow if needed

---

## Testing the API

### Using the Interactive Docs
1. Start server: `./run_dev.sh`
2. Open browser: http://localhost:8000/docs
3. Try endpoints with "Try it out" button

### Using curl

**Request OTP:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/otp/request" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+14155551234"}'
```

**Verify OTP:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/otp/verify" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+14155551234", "code": "123456"}'
```

**Create Driver Profile:**
```bash
curl -X POST "http://localhost:8000/api/v1/drivers" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "handle": "trucker_mike",
    "avatar_id": "avatar_123",
    "status": "parked"
  }'
```

---

## Database Schema

The API works with these Supabase tables:
- `auth.users` - Supabase auth users
- `drivers` - Driver profiles
- `driver_locations` - Location tracking
- `status_history` - Status change history
- `facilities` - Truck stops, rest areas, etc.

---

## Environment Variables Required

```bash
# Supabase
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY="sb_publishable_..."  # For client operations
SUPABASE_SECRET_KEY="sb_secret_..."           # For admin operations

# Database
DATABASE_URL="postgresql://..."

# JWT
JWT_SECRET_KEY="your-secret-key"

# Server
HOST="0.0.0.0"
PORT=8000
DEBUG=True
ENVIRONMENT="development"
```

---

## Error Handling

All endpoints return consistent error format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "timestamp": 1234567890
  }
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found
- `500` - Internal Server Error
