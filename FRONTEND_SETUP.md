# Frontend Setup Guide

## 🎯 Quick Start - Get Your Frontend Connected in 5 Minutes

---

## Step 1: Make Sure Backend is Running

```bash
cd finddriverbackend
./run_dev.sh
```

You should see:
```
🚀 Starting Find a Truck Driver API
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Test it:** Open http://localhost:8000/health in your browser

---

## Step 2: Update Your Frontend Config

### Create or update `config/api.ts` in your React Native project:

```typescript
// config/api.ts
const API_BASE = 'http://localhost:8000/api/v1';

export const API_ENDPOINTS = {
  // Auth - Email OTP (Passwordless)
  emailOtpRequest: `${API_BASE}/auth/email/otp/request`,
  emailOtpVerify: `${API_BASE}/auth/email/otp/verify`,
  refreshToken: `${API_BASE}/auth/token/refresh`,

  // Driver Profile
  createProfile: `${API_BASE}/drivers`,
  getMyProfile: `${API_BASE}/drivers/me`,
  updateProfile: `${API_BASE}/drivers/me`,

  // Location
  checkIn: `${API_BASE}/locations/check-in`,
  updateStatus: `${API_BASE}/locations/status/update`,
  nearbyDrivers: `${API_BASE}/locations/nearby`,

  // Map
  mapDrivers: `${API_BASE}/map/drivers`,
  mapStats: `${API_BASE}/map/stats`,
};
```

⚠️ **Important:** All endpoints MUST include `/api/v1/` in the path!

---

## Step 3: Test Authentication

### Test with curl first:

```bash
# 1. Request OTP
curl -X POST http://localhost:8000/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com"}'

# 2. Check your email for the 8-digit code

# 3. Verify OTP (replace CODE with actual code from email)
curl -X POST http://localhost:8000/api/v1/auth/email/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@gmail.com", "code": "12345678"}'
```

If this works, your backend is ready!

---

## Step 4: Implement in React Native

### Authentication Service

```typescript
// services/auth.ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_ENDPOINTS } from '../config/api';

export const AuthService = {
  async requestEmailOTP(email: string) {
    const response = await fetch(API_ENDPOINTS.emailOtpRequest, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) throw new Error('Failed to send OTP');
    return await response.json();
  },

  async verifyEmailOTP(email: string, code: string) {
    const response = await fetch(API_ENDPOINTS.emailOtpVerify, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    });

    if (!response.ok) throw new Error('Invalid code');

    const data = await response.json();

    // Save tokens
    await AsyncStorage.setItem('access_token', data.tokens.access_token);
    await AsyncStorage.setItem('refresh_token', data.tokens.refresh_token);

    return data;
  },
};
```

### Login Screen

```typescript
// screens/LoginScreen.tsx
import { useState } from 'react';
import { View, TextInput, Button, Alert } from 'react-native';
import { AuthService } from '../services/auth';

export function LoginScreen({ navigation }) {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'email' | 'code'>('email');

  const requestCode = async () => {
    try {
      await AuthService.requestEmailOTP(email);
      setStep('code');
      Alert.alert('Check your email', 'We sent you an 8-digit code');
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const verifyCode = async () => {
    try {
      const data = await AuthService.verifyEmailOTP(email, code);

      if (data.driver) {
        navigation.navigate('Home');
      } else {
        navigation.navigate('Onboarding');
      }
    } catch (error) {
      Alert.alert('Error', 'Invalid code');
    }
  };

  if (step === 'email') {
    return (
      <View>
        <TextInput
          value={email}
          onChangeText={setEmail}
          placeholder="Enter your email"
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <Button title="Send Code" onPress={requestCode} />
      </View>
    );
  }

  return (
    <View>
      <TextInput
        value={code}
        onChangeText={setCode}
        placeholder="Enter 8-digit code"
        keyboardType="number-pad"
        maxLength={8}
      />
      <Button title="Verify & Login" onPress={verifyCode} />
      <Button title="Change Email" onPress={() => setStep('email')} />
    </View>
  );
}
```

---

## Step 5: Test It!

1. Run your React Native app
2. Enter your email
3. Check your email for the 8-digit code
4. Enter the code
5. You should be logged in!

---

## 🆘 Troubleshooting

### "404 Not Found"
Your URL is missing `/api/v1/`.

**Wrong:** `http://localhost:8000/auth/email/otp/request`
**Right:** `http://localhost:8000/api/v1/auth/email/otp/request`

### "Network Request Failed" (Physical Device)
You're using `localhost` on a physical device. Use your computer's IP instead:

```typescript
const API_BASE = 'http://192.168.1.XXX:8000/api/v1';  // Replace XXX with your IP
```

Find your IP:
- **Mac:** Run `ipconfig getifaddr en0`
- **Windows:** Run `ipconfig` (look for IPv4 Address)

### "Email Not Received"
1. Check spam folder
2. Go to http://localhost:8000/docs and test the endpoint there
3. Check backend logs: `tail -f logs/app.log`

### "Invalid Code"
- Code must be exactly **8 digits** (Supabase default)
- Code expires in **1 hour**
- Email must match exactly

---

## 📚 Complete Documentation

For more detailed guides, see:

- **[docs/QUICK_START_FRONTEND.md](./docs/QUICK_START_FRONTEND.md)** - All endpoints with examples
- **[docs/API_URLS_REFERENCE.md](./docs/API_URLS_REFERENCE.md)** - Complete endpoint list
- **[docs/FRONTEND_TROUBLESHOOTING.md](./docs/FRONTEND_TROUBLESHOOTING.md)** - Common issues & solutions
- **[docs/FRONTEND_INTEGRATION.md](./docs/FRONTEND_INTEGRATION.md)** - Full integration guide

**Interactive API Docs:** http://localhost:8000/docs

---

## 🎉 You're Ready!

Your backend has:
- ✅ Email OTP authentication (free, no SMS costs)
- ✅ Driver profiles with status tracking
- ✅ Location check-in with privacy fuzzing
- ✅ Nearby driver search
- ✅ Map clustering and hotspots

Follow the examples above and you'll have a working integration in minutes!

**Need help?** Check [docs/FRONTEND_TROUBLESHOOTING.md](./docs/FRONTEND_TROUBLESHOOTING.md) for solutions to common issues.
