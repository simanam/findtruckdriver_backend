# API URLs Quick Reference

## 🎯 Base URL
```
http://localhost:8000
```

---

## 📋 All Endpoints (Copy & Paste Ready)

### Authentication

```
POST   http://localhost:8000/api/v1/auth/email/otp/request
POST   http://localhost:8000/api/v1/auth/email/otp/verify
POST   http://localhost:8000/api/v1/auth/otp/request
POST   http://localhost:8000/api/v1/auth/otp/verify
POST   http://localhost:8000/api/v1/auth/magic-link/request
POST   http://localhost:8000/api/v1/auth/token/refresh
POST   http://localhost:8000/api/v1/auth/logout
GET    http://localhost:8000/api/v1/auth/me
```

### Driver Profile

```
POST   http://localhost:8000/api/v1/drivers
GET    http://localhost:8000/api/v1/drivers/me
PATCH  http://localhost:8000/api/v1/drivers/me
PATCH  http://localhost:8000/api/v1/drivers/me/status
GET    http://localhost:8000/api/v1/drivers/{handle}
GET    http://localhost:8000/api/v1/drivers/id/{driver_id}
```

### Location & Check-in

```
POST   http://localhost:8000/api/v1/locations/check-in
POST   http://localhost:8000/api/v1/locations/status/update
GET    http://localhost:8000/api/v1/locations/me
GET    http://localhost:8000/api/v1/locations/nearby?latitude=34.0522&longitude=-118.2437&radius_miles=10
```

### Map & Search

```
GET    http://localhost:8000/api/v1/map/drivers?latitude=34.0522&longitude=-118.2437&radius_miles=25
GET    http://localhost:8000/api/v1/map/clusters?latitude=34.0522&longitude=-118.2437&radius_miles=50
GET    http://localhost:8000/api/v1/map/hotspots?latitude=34.0522&longitude=-118.2437&radius_miles=100
GET    http://localhost:8000/api/v1/map/stats?latitude=34.0522&longitude=-118.2437&radius_miles=50
```

---

## 🔑 Most Important Endpoints

### 1. Login Flow
```javascript
// Step 1: Request OTP
POST http://localhost:8000/api/v1/auth/email/otp/request
Body: { "email": "driver@example.com" }

// Step 2: Verify OTP (user enters code from email)
POST http://localhost:8000/api/v1/auth/email/otp/verify
Body: { "email": "driver@example.com", "code": "12345678" }
```

### 2. Onboarding
```javascript
// Create profile after login
POST http://localhost:8000/api/v1/drivers
Headers: Authorization: Bearer YOUR_TOKEN
Body: {
  "handle": "trucker_mike",
  "avatar_id": "avatar_001",
  "status": "parked"
}
```

### 3. Update Status
```javascript
// Change status with location
POST http://localhost:8000/api/v1/locations/status/update
Headers: Authorization: Bearer YOUR_TOKEN
Body: {
  "status": "waiting",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "accuracy": 10.0
}
```

### 4. Find Nearby Drivers
```javascript
// Search for drivers (no auth needed)
GET http://localhost:8000/api/v1/locations/nearby?latitude=34.0522&longitude=-118.2437&radius_miles=10&status_filter=waiting
```

---

## 📱 React Native Config

```typescript
// config/api.ts
export const API_BASE_URL = 'http://localhost:8000';
export const API_VERSION = '/api/v1';

// Helper to build URLs
export const buildUrl = (endpoint: string) => {
  return `${API_BASE_URL}${API_VERSION}${endpoint}`;
};

// Usage
const url = buildUrl('/auth/email/otp/request');
// Result: http://localhost:8000/api/v1/auth/email/otp/request
```

---

## 🧪 Test with curl

```bash
# Test 1: Request OTP
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com"}'

# Test 2: Verify OTP (check your email first!)
curl -X POST http://localhost:8000/api/v1/auth/email/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com", "code": "12345678"}'

# Test 3: Get profile (replace TOKEN)
curl http://localhost:8000/api/v1/drivers/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## ⚠️ Common Mistakes

### ❌ WRONG
```
http://localhost:8000/auth/email/otp/request        (missing /api/v1)
http://localhost:8000/api/auth/email/otp/request    (missing /v1)
http://localhost:8000/v1/auth/email/otp/request     (missing /api)
```

### ✅ CORRECT
```
http://localhost:8000/api/v1/auth/email/otp/request
```

---

## 🌐 For Physical Device Testing

Replace `localhost` with your computer's IP address:

```typescript
// Find your IP address:
// Mac: Run "ipconfig getifaddr en0" in terminal
// Windows: Run "ipconfig" and look for IPv4 Address

const API_BASE_URL = 'http://192.168.1.100:8000';  // Use your actual IP
```

---

## 📚 Full Documentation

- **Interactive Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Quick Start:** [QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md)
- **Complete Guide:** [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md)
