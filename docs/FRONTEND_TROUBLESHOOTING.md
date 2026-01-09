# Frontend Integration Troubleshooting

## 🔍 Common Issues & Solutions

---

## Issue 1: 404 Not Found

### Symptoms
```
POST /auth/email/otp/request HTTP/1.1" 404 Not Found
```

### Cause
Missing `/api/v1/` prefix in the URL

### ❌ Wrong Code
```typescript
fetch('http://localhost:8000/auth/email/otp/request', {
  // Missing /api/v1/
})
```

### ✅ Fixed Code
```typescript
fetch('http://localhost:8000/api/v1/auth/email/otp/request', {
  // Correct: includes /api/v1/
})
```

### Quick Fix
Update your `config/api.ts`:
```typescript
const API_BASE = 'http://localhost:8000/api/v1';  // Include /api/v1

export const API_ENDPOINTS = {
  emailOtpRequest: `${API_BASE}/auth/email/otp/request`,
  emailOtpVerify: `${API_BASE}/auth/email/otp/verify`,
  // ...
};
```

---

## Issue 2: 401 Unauthorized

### Symptoms
```
GET /api/v1/drivers/me HTTP/1.1" 401 Unauthorized
```

### Cause
Missing or invalid `Authorization` header

### ❌ Wrong Code
```typescript
// Missing Authorization header
fetch('http://localhost:8000/api/v1/drivers/me', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
})
```

### ✅ Fixed Code
```typescript
const token = await AsyncStorage.getItem('access_token');

fetch('http://localhost:8000/api/v1/drivers/me', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,  // ← Include token
    'Content-Type': 'application/json'
  }
})
```

### Debug Checklist
1. **Token exists?**
   ```typescript
   const token = await AsyncStorage.getItem('access_token');
   console.log('Token:', token);  // Should not be null
   ```

2. **Correct format?**
   ```typescript
   // Must include "Bearer " prefix with space
   'Authorization': `Bearer ${token}`  // ✅ Correct
   'Authorization': token              // ❌ Wrong
   'Authorization': `${token}`         // ❌ Wrong
   ```

3. **Token expired?**
   ```typescript
   // If token expired, refresh it
   const refreshToken = await AsyncStorage.getItem('refresh_token');
   const response = await fetch('http://localhost:8000/api/v1/auth/token/refresh', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ refresh_token: refreshToken })
   });
   const data = await response.json();
   await AsyncStorage.setItem('access_token', data.access_token);
   ```

---

## Issue 3: Network Request Failed (Physical Device)

### Symptoms
```
Error: Network request failed
TypeError: Network request failed
```

### Cause
Using `localhost` on physical device (only works on simulator/emulator)

### ❌ Wrong Code
```typescript
// This only works on iOS Simulator / Android Emulator
const API_URL = 'http://localhost:8000';
```

### ✅ Fixed Code
```typescript
// Use your computer's actual IP address
const API_URL = 'http://192.168.1.100:8000';  // Replace with your IP
```

### How to Find Your IP Address

**On Mac:**
```bash
ipconfig getifaddr en0
# Output: 192.168.1.100
```

**On Windows:**
```bash
ipconfig
# Look for "IPv4 Address" under your active network adapter
# Example: 192.168.1.100
```

**Then update your config:**
```typescript
// config/api.ts
export const API_URL = __DEV__
  ? Platform.OS === 'ios'
    ? 'http://localhost:8000'           // iOS Simulator
    : 'http://10.0.2.2:8000'             // Android Emulator
  : 'https://api.findatruckdriver.com';  // Production

// Or for physical device testing:
// export const API_URL = 'http://192.168.1.100:8000';
```

### Pro Tip: Auto-detect
```typescript
import { Platform } from 'react-native';

const getApiUrl = () => {
  if (__DEV__) {
    // Development
    if (Platform.OS === 'ios') {
      return 'http://localhost:8000';     // iOS Simulator
    } else if (Platform.OS === 'android') {
      return 'http://10.0.2.2:8000';      // Android Emulator
    }
  }
  return 'https://api.findatruckdriver.com';  // Production
};

export const API_URL = getApiUrl();
```

---

## Issue 4: CORS Error (Web/Browser)

### Symptoms
```
Access to fetch at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

### Cause
Browser blocking cross-origin requests

### Solution
Backend is already configured for CORS. Check your CORS settings:

**In backend `.env`:**
```bash
CORS_ORIGINS=["http://localhost:3000","http://localhost:19006"]
```

**If using different port, add it:**
```bash
CORS_ORIGINS=["http://localhost:3000","http://localhost:8081","http://localhost:19006"]
```

---

## Issue 5: Invalid OTP Code

### Symptoms
```
{
  "detail": "Invalid OTP code or expired"
}
```

### Common Causes

1. **Wrong code length**
   - Backend expects **8 digits** (Supabase default)
   - Check your Supabase settings: Dashboard → Auth → Providers → Email → Email OTP Length

2. **Code expired**
   - Default expiry: 1 hour (3600 seconds)
   - Request new code if expired

3. **Typo in email**
   - Email in verify request must exactly match email in request

### Debug Code
```typescript
// Request OTP
console.log('Requesting OTP for:', email);
await requestEmailOTP(email);

// Verify OTP
console.log('Verifying code:', code, 'for email:', email);
console.log('Code length:', code.length);  // Should be 8

if (code.length !== 8) {
  Alert.alert('Invalid code', 'Please enter all 8 digits');
  return;
}

await verifyEmailOTP(email, code);
```

---

## Issue 6: Received Magic Link Instead of OTP Code

### Symptoms
```
Email contains a clickable link like:
http://localhost:3000/#access_token=...

Instead of an 8-digit code like: 12345678
```

### Cause
Backend was missing `"channel": "email"` parameter in the OTP request.

### ✅ Fixed!
This issue is now fixed in the backend code. The endpoint now includes:
```python
"channel": "email"  # Forces OTP code (not magic link)
```

### Test the Fix
```bash
# Restart backend if needed
cd finddriverbackend
./run_dev.sh

# Request OTP again
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com"}'

# Check email - you should now get an 8-digit code!
```

**See [EMAIL_OTP_VS_MAGIC_LINK.md](./EMAIL_OTP_VS_MAGIC_LINK.md) for details.**

---

## Issue 7: Email Not Received

### Symptoms
User doesn't receive OTP email

### Debug Steps

1. **Check Supabase Logs**
   - Go to Supabase Dashboard → Authentication → Logs
   - Look for email send events
   - Check for errors

2. **Check Spam Folder**
   - Supabase emails often land in spam
   - Mark as "Not Spam" to improve deliverability

3. **Test with Different Email**
   - Try Gmail, Outlook, etc.
   - Some providers may block automated emails

4. **Check Email Provider Status**
   - Go to Supabase Dashboard → Auth → Providers → Email
   - Make sure "Enable Email Provider" is ON

5. **Backend Logs**
   ```bash
   # In backend terminal, check for errors
   tail -f logs/app.log
   ```

### Verify Backend Response
```typescript
const response = await fetch('http://localhost:8000/api/v1/auth/email/otp/request', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email })
});

console.log('Status:', response.status);  // Should be 200
const data = await response.json();
console.log('Response:', data);
// Expected: { success: true, message: "Verification code sent to...", email: "..." }
```

---

## Issue 7: Handle Already Exists

### Symptoms
```
{
  "detail": "Handle 'trucker_mike' is already taken"
}
```

### Solution
```typescript
try {
  await createProfile(handle, avatarId, status);
} catch (error) {
  if (error.message.includes('already taken')) {
    Alert.alert(
      'Handle taken',
      'This handle is already in use. Please choose another.',
      [{ text: 'OK' }]
    );
  }
}
```

---

## Issue 8: Location Permission Denied

### Symptoms
```
Error: Location permission denied
```

### Solution

**iOS - Add to Info.plist:**
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>We need your location to show nearby drivers</string>
<key>NSLocationAlwaysUsageDescription</key>
<string>We need your location to update your status</string>
```

**Android - Add to AndroidManifest.xml:**
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

**Request Permission:**
```typescript
import * as Location from 'expo-location';

const requestLocation = async () => {
  const { status } = await Location.requestForegroundPermissionsAsync();

  if (status !== 'granted') {
    Alert.alert(
      'Permission Denied',
      'We need location permission to show nearby drivers',
      [{ text: 'OK' }]
    );
    return null;
  }

  const location = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.High,
  });

  return location.coords;
};
```

---

## Issue 9: Response is not JSON

### Symptoms
```
SyntaxError: Unexpected token < in JSON at position 0
```

### Cause
Backend returned HTML error page instead of JSON

### Debug
```typescript
const response = await fetch(url);

console.log('Status:', response.status);
console.log('Content-Type:', response.headers.get('content-type'));

const text = await response.text();
console.log('Raw response:', text);

// Then parse JSON only if it's actually JSON
if (response.headers.get('content-type')?.includes('application/json')) {
  const data = JSON.parse(text);
} else {
  console.error('Expected JSON, got:', text);
}
```

---

## Issue 10: Server Not Running

### Symptoms
```
Error: connect ECONNREFUSED 127.0.0.1:8000
```

### Solution

1. **Start backend server:**
   ```bash
   cd finddriverbackend
   ./run_dev.sh
   ```

2. **Verify server is running:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy",...}
   ```

3. **Check backend logs:**
   ```bash
   tail -f logs/app.log
   ```

---

## 🛠️ Debugging Tools

### 1. Log All Requests
```typescript
// utils/api-debug.ts
export const debugFetch = async (url: string, options?: RequestInit) => {
  console.log('🌐 Request:', options?.method || 'GET', url);
  console.log('📤 Headers:', options?.headers);
  console.log('📦 Body:', options?.body);

  const response = await fetch(url, options);

  console.log('✅ Response:', response.status, response.statusText);
  const text = await response.text();
  console.log('📥 Body:', text);

  return { response, text };
};

// Usage
const { response, text } = await debugFetch(
  'http://localhost:8000/api/v1/auth/email/otp/request',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'test@example.com' })
  }
);
```

### 2. Test Backend with curl
```bash
# Always test with curl first to verify backend works
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

### 3. Use Swagger UI
```
http://localhost:8000/docs
```
- Test all endpoints interactively
- See exact request/response formats
- Verify backend is working

---

## 📋 Pre-Flight Checklist

Before debugging, verify:

- [ ] Backend server is running (`./run_dev.sh`)
- [ ] Can access http://localhost:8000/health
- [ ] Using correct URL with `/api/v1/` prefix
- [ ] Content-Type header is set for POST requests
- [ ] Authorization header included for protected endpoints
- [ ] Using correct IP address (if testing on physical device)
- [ ] Location permissions granted (if using location features)
- [ ] Email provider enabled in Supabase (for email OTP)

---

## 🆘 Still Having Issues?

1. **Check backend logs:**
   ```bash
   tail -f finddriverbackend/logs/app.log
   ```

2. **Test with Swagger UI:**
   - http://localhost:8000/docs
   - If it works there, issue is in frontend code

3. **Compare with working example:**
   - See [QUICK_START_FRONTEND.md](./QUICK_START_FRONTEND.md)
   - Copy exact code examples

4. **Check network in React Native Debugger:**
   - Enable Network Inspect
   - See exact requests being sent

5. **Test endpoint with curl:**
   ```bash
   curl -v http://localhost:8000/api/v1/auth/email/otp/request \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com"}'
   ```
   If curl works but app doesn't, issue is in app code.

---

## 📚 Additional Resources

- [API URLs Reference](./API_URLS_REFERENCE.md) - All endpoints
- [Quick Start Guide](./QUICK_START_FRONTEND.md) - Working code examples
- [Full Integration Guide](./FRONTEND_INTEGRATION.md) - Complete implementation
- [Swagger Docs](http://localhost:8000/docs) - Interactive API testing
