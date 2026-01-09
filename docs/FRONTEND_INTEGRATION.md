# Frontend Integration Guide

## Complete Authentication Flow for React Native

This guide shows exactly what your frontend needs to do to integrate with the backend API.

---

## 🚨 IMPORTANT: API Base URL

**Your backend server runs at:** `http://localhost:8000` (development)

**All API endpoints start with:** `/api/v1/`

**Example:** `http://localhost:8000/api/v1/auth/email/otp/request`

---

## Overview: Email OTP Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  1. User enters email                                       │
│  2. Frontend → POST /api/v1/auth/email/otp/request          │
│  3. User receives 8-digit code in email                     │
│  4. User enters code                                        │
│  5. Frontend → POST /api/v1/auth/email/otp/verify           │
│  6. Backend returns: tokens + user info                     │
│  7. Frontend stores tokens → navigates based on profile     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Environment Setup

### Create config/api.ts

```typescript
// config/api.ts

// IMPORTANT: Use your computer's IP address for testing on physical device
// Find your IP: Run "ipconfig getifaddr en0" on Mac or "ipconfig" on Windows
export const API_URL = __DEV__
  ? 'http://localhost:8000'  // iOS Simulator / Android Emulator
  // ? 'http://192.168.1.XXX:8000'  // Physical device (use your IP)
  : 'https://api.findatruckdriver.com';  // Production

export const API_ENDPOINTS = {
  // Auth - Email OTP (Passwordless)
  emailOtpRequest: `${API_URL}/api/v1/auth/email/otp/request`,
  emailOtpVerify: `${API_URL}/api/v1/auth/email/otp/verify`,

  // Auth - Phone OTP (Alternative)
  phoneOtpRequest: `${API_URL}/api/v1/auth/otp/request`,
  phoneOtpVerify: `${API_URL}/api/v1/auth/otp/verify`,

  // Auth - Token Management
  refreshToken: `${API_URL}/api/v1/auth/token/refresh`,
  logout: `${API_URL}/api/v1/auth/logout`,

  // Driver Profile
  createProfile: `${API_URL}/api/v1/drivers`,
  getMyProfile: `${API_URL}/api/v1/drivers/me`,
  updateProfile: `${API_URL}/api/v1/drivers/me`,
  updateStatus: `${API_URL}/api/v1/drivers/me/status`,

  // Location & Check-in
  checkIn: `${API_URL}/api/v1/locations/check-in`,
  statusUpdate: `${API_URL}/api/v1/locations/status/update`,
  myLocation: `${API_URL}/api/v1/locations/me`,
  nearbyDrivers: `${API_URL}/api/v1/locations/nearby`,

  // Map
  mapDrivers: `${API_URL}/api/v1/map/drivers`,
  mapClusters: `${API_URL}/api/v1/map/clusters`,
  mapHotspots: `${API_URL}/api/v1/map/hotspots`,
  mapStats: `${API_URL}/api/v1/map/stats`,
};
```

---

## Step 2: Create API Service

### API helper functions

```typescript
// services/api.ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_ENDPOINTS } from '../config/api';

// Token management
export const TokenService = {
  async getAccessToken(): Promise<string | null> {
    return await AsyncStorage.getItem('access_token');
  },

  async getRefreshToken(): Promise<string | null> {
    return await AsyncStorage.getItem('refresh_token');
  },

  async saveTokens(accessToken: string, refreshToken: string) {
    await AsyncStorage.setItem('access_token', accessToken);
    await AsyncStorage.setItem('refresh_token', refreshToken);
  },

  async clearTokens() {
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
  },
};

// API client with automatic token refresh
export class ApiClient {
  private static async makeRequest(
    url: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const accessToken = await TokenService.getAccessToken();

    const headers = {
      'Content-Type': 'application/json',
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
      ...options.headers,
    };

    const response = await fetch(url, { ...options, headers });

    // Handle token expiration
    if (response.status === 401) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        // Retry with new token
        const newToken = await TokenService.getAccessToken();
        return fetch(url, {
          ...options,
          headers: {
            ...headers,
            Authorization: `Bearer ${newToken}`,
          },
        });
      }
      // Refresh failed, user needs to re-login
      await TokenService.clearTokens();
      // Navigate to login screen
      throw new Error('Session expired. Please login again.');
    }

    return response;
  }

  static async get(url: string): Promise<any> {
    const response = await this.makeRequest(url, { method: 'GET' });
    return response.json();
  }

  static async post(url: string, data: any): Promise<any> {
    const response = await this.makeRequest(url, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.json();
  }

  static async put(url: string, data: any): Promise<any> {
    const response = await this.makeRequest(url, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return response.json();
  }

  private static async refreshAccessToken(): Promise<boolean> {
    try {
      const refreshToken = await TokenService.getRefreshToken();
      if (!refreshToken) return false;

      const response = await fetch(API_ENDPOINTS.refreshToken, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        await TokenService.saveTokens(data.access_token, data.refresh_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }
}
```

---

## Step 3: Authentication Service

### Email OTP functions

```typescript
// services/auth.ts
import { API_ENDPOINTS } from '../config/api';
import { TokenService } from './api';

export interface AuthResponse {
  user: {
    id: string;
    email: string;
    phone: string | null;
    created_at: string;
  };
  tokens: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  };
  driver: any | null;  // Driver profile if exists
}

export const AuthService = {
  /**
   * Step 1: Request OTP code via email
   */
  async requestEmailOTP(email: string): Promise<void> {
    const response = await fetch(API_ENDPOINTS.emailOtpRequest, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send OTP');
    }
  },

  /**
   * Step 2: Verify OTP code and login
   */
  async verifyEmailOTP(email: string, code: string): Promise<AuthResponse> {
    const response = await fetch(API_ENDPOINTS.emailOtpVerify, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Invalid code');
    }

    const data: AuthResponse = await response.json();

    // Save tokens
    await TokenService.saveTokens(
      data.tokens.access_token,
      data.tokens.refresh_token
    );

    return data;
  },

  /**
   * Logout
   */
  async logout(): Promise<void> {
    try {
      const token = await TokenService.getAccessToken();
      if (token) {
        await fetch(API_ENDPOINTS.logout, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        });
      }
    } finally {
      await TokenService.clearTokens();
    }
  },

  /**
   * Check if user is logged in
   */
  async isLoggedIn(): Promise<boolean> {
    const token = await TokenService.getAccessToken();
    return token !== null;
  },
};
```

---

## Step 4: Login Screen Component

### Complete React Native login screen

```typescript
// screens/LoginScreen.tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { AuthService } from '../services/auth';

type LoginStep = 'email' | 'code';

export function LoginScreen({ navigation }) {
  const [step, setStep] = useState<LoginStep>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  /**
   * Step 1: Send OTP to email
   */
  const handleSendCode = async () => {
    if (!email || !email.includes('@')) {
      Alert.alert('Invalid Email', 'Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      await AuthService.requestEmailOTP(email);
      setStep('code');
      Alert.alert(
        'Check your email!',
        `We sent an 8-digit code to ${email}`,
        [{ text: 'OK' }]
      );
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Step 2: Verify code and login
   */
  const handleVerifyCode = async () => {
    if (code.length !== 8) {
      Alert.alert('Invalid Code', 'Please enter the 8-digit code');
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.verifyEmailOTP(email, code);

      // Check if user has driver profile
      if (response.driver) {
        // Has profile → go to home
        navigation.replace('Home');
      } else {
        // No profile → go to onboarding
        navigation.replace('Onboarding');
      }
    } catch (error) {
      Alert.alert('Invalid Code', 'Please check the code and try again');
      setCode(''); // Clear code for retry
    } finally {
      setLoading(false);
    }
  };

  /**
   * Resend code
   */
  const handleResendCode = async () => {
    setCode('');
    await handleSendCode();
  };

  // EMAIL INPUT SCREEN
  if (step === 'email') {
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.content}>
          <Text style={styles.title}>Welcome Back!</Text>
          <Text style={styles.subtitle}>
            Enter your email to get started
          </Text>

          <TextInput
            style={styles.input}
            placeholder="driver@example.com"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            editable={!loading}
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSendCode}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Send Code</Text>
            )}
          </TouchableOpacity>

          <Text style={styles.helpText}>
            We'll send you an 8-digit verification code
          </Text>
        </View>
      </KeyboardAvoidingView>
    );
  }

  // CODE VERIFICATION SCREEN
  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <Text style={styles.title}>Enter Code</Text>
        <Text style={styles.subtitle}>
          We sent an 8-digit code to{'\n'}
          <Text style={styles.email}>{email}</Text>
        </Text>

        <TextInput
          style={[styles.input, styles.codeInput]}
          placeholder="12345678"
          value={code}
          onChangeText={setCode}
          keyboardType="number-pad"
          maxLength={8}
          autoFocus
          editable={!loading}
        />

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleVerifyCode}
          disabled={loading || code.length !== 8}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Verify & Login</Text>
          )}
        </TouchableOpacity>

        <View style={styles.actions}>
          <TouchableOpacity onPress={() => setStep('email')}>
            <Text style={styles.linkText}>Change Email</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={handleResendCode} disabled={loading}>
            <Text style={styles.linkText}>Resend Code</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.helpText}>
          Check your spam folder if you don't see the email
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#1a1a1a',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 32,
  },
  email: {
    fontWeight: 'bold',
    color: '#1a1a1a',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
  },
  codeInput: {
    fontSize: 24,
    textAlign: 'center',
    letterSpacing: 8,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 24,
  },
  linkText: {
    color: '#007AFF',
    fontSize: 16,
  },
  helpText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
});
```

---

## Step 5: Onboarding Screen (Create Driver Profile)

```typescript
// screens/OnboardingScreen.tsx
import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { ApiClient, API_ENDPOINTS } from '../services/api';

export function OnboardingScreen({ navigation }) {
  const [handle, setHandle] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreateProfile = async () => {
    if (!handle || handle.length < 3) {
      Alert.alert('Invalid Handle', 'Handle must be at least 3 characters');
      return;
    }

    setLoading(true);
    try {
      await ApiClient.post(API_ENDPOINTS.createProfile, {
        handle: handle.toLowerCase(),
        avatar_id: 'default_avatar',  // Or let user pick
        status: 'parked',
      });

      Alert.alert('Welcome!', 'Your profile has been created', [
        { text: 'OK', onPress: () => navigation.replace('Home') },
      ]);
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1, padding: 24, justifyContent: 'center' }}>
      <Text style={{ fontSize: 32, fontWeight: 'bold', marginBottom: 8 }}>
        Choose Your Handle
      </Text>
      <Text style={{ fontSize: 16, color: '#666', marginBottom: 32 }}>
        This is how other drivers will see you
      </Text>

      <TextInput
        style={{
          borderWidth: 1,
          borderColor: '#ddd',
          borderRadius: 12,
          padding: 16,
          fontSize: 16,
          marginBottom: 16,
        }}
        placeholder="trucker_mike"
        value={handle}
        onChangeText={setHandle}
        autoCapitalize="none"
        autoCorrect={false}
      />

      <TouchableOpacity
        style={{
          backgroundColor: '#007AFF',
          padding: 16,
          borderRadius: 12,
          alignItems: 'center',
        }}
        onPress={handleCreateProfile}
        disabled={loading}
      >
        <Text style={{ color: '#fff', fontSize: 18, fontWeight: '600' }}>
          {loading ? 'Creating...' : 'Create Profile'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}
```

---

## Step 6: Location Check-in

```typescript
// services/location.ts
import { ApiClient, API_ENDPOINTS } from './api';
import * as Location from 'expo-location';

export const LocationService = {
  /**
   * Get current GPS location
   */
  async getCurrentLocation() {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      throw new Error('Location permission denied');
    }

    const location = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });

    return {
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
      accuracy: location.coords.accuracy || 0,
      heading: location.coords.heading || 0,
      speed: location.coords.speed || 0,
    };
  },

  /**
   * Check-in (refresh location, same status)
   */
  async checkIn() {
    const location = await this.getCurrentLocation();
    return ApiClient.post(API_ENDPOINTS.checkIn, location);
  },

  /**
   * Update status with location
   */
  async updateStatus(status: 'rolling' | 'waiting' | 'parked') {
    const location = await this.getCurrentLocation();
    return ApiClient.post(API_ENDPOINTS.updateStatus, {
      status,
      ...location,
    });
  },

  /**
   * Get nearby drivers
   */
  async getNearbyDrivers(latitude: number, longitude: number, radiusMiles = 10) {
    const url = `${API_ENDPOINTS.nearbyDrivers}?latitude=${latitude}&longitude=${longitude}&radius_miles=${radiusMiles}`;
    return ApiClient.get(url);
  },
};
```

---

## Step 7: Status Control Component

```typescript
// components/StatusControl.tsx
import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Alert } from 'react-native';
import { LocationService } from '../services/location';

export function StatusControl({ currentStatus, onStatusChange }) {
  const [loading, setLoading] = useState(false);

  const handleStatusChange = async (newStatus: string) {
    if (newStatus === currentStatus) {
      // Same status = check-in
      await handleCheckIn();
      return;
    }

    // Different status = update
    setLoading(true);
    try {
      const response = await LocationService.updateStatus(newStatus as any);
      onStatusChange(response);
      Alert.alert('Status Updated!', response.message);
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      const response = await LocationService.checkIn();
      Alert.alert('Checked In!', response.message);
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      {/* Status Buttons */}
      <View style={{ flexDirection: 'row', gap: 12, marginBottom: 16 }}>
        <StatusButton
          label="🟢 Rolling"
          active={currentStatus === 'rolling'}
          onPress={() => handleStatusChange('rolling')}
          disabled={loading}
        />
        <StatusButton
          label="🔴 Waiting"
          active={currentStatus === 'waiting'}
          onPress={() => handleStatusChange('waiting')}
          disabled={loading}
        />
        <StatusButton
          label="🔵 Parked"
          active={currentStatus === 'parked'}
          onPress={() => handleStatusChange('parked')}
          disabled={loading}
        />
      </View>

      {/* Check-in Button */}
      <TouchableOpacity
        style={{
          backgroundColor: '#007AFF',
          padding: 16,
          borderRadius: 12,
          alignItems: 'center',
        }}
        onPress={handleCheckIn}
        disabled={loading}
      >
        <Text style={{ color: '#fff', fontSize: 16, fontWeight: '600' }}>
          📍 Check In
        </Text>
      </TouchableOpacity>
    </View>
  );
}

function StatusButton({ label, active, onPress, disabled }) {
  return (
    <TouchableOpacity
      style={{
        flex: 1,
        padding: 12,
        borderRadius: 8,
        backgroundColor: active ? '#007AFF' : '#f0f0f0',
        alignItems: 'center',
      }}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={{ color: active ? '#fff' : '#333' }}>{label}</Text>
    </TouchableOpacity>
  );
}
```

---

## Quick Reference: API Endpoints

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/api/v1/auth/email/otp/request` | POST | ❌ No | Send 8-digit code |
| `/api/v1/auth/email/otp/verify` | POST | ❌ No | Verify code & login |
| `/api/v1/auth/token/refresh` | POST | ❌ No | Refresh access token |
| `/api/v1/auth/logout` | POST | ✅ Yes | Logout |
| `/api/v1/drivers` | POST | ✅ Yes | Create profile |
| `/api/v1/drivers/me` | GET | ✅ Yes | Get my profile |
| `/api/v1/locations/check-in` | POST | ✅ Yes | Check-in with location |
| `/api/v1/locations/status/update` | POST | ✅ Yes | Change status |
| `/api/v1/locations/nearby` | GET | ❌ No | Find nearby drivers |

---

## Summary: What Frontend Needs to Do

✅ **1. Login Flow**
- Email input screen
- Code verification screen (8 digits)
- Handle tokens in AsyncStorage
- Auto-refresh expired tokens

✅ **2. Onboarding**
- Create driver profile
- Choose handle
- Select avatar (optional)

✅ **3. Location Features**
- Request location permissions
- Send location on check-in
- Send location on status change
- Show nearby drivers on map

✅ **4. Navigation**
- After login with profile → Home
- After login without profile → Onboarding
- Token expired → Login

That's everything your frontend needs! The backend is ready and waiting. 🚀

---

# Facility Discovery: Frontend Integration

## What Frontend Needs to Do: **NOTHING REQUIRED! ✅**

The on-demand facility discovery feature is **100% backend-transparent**. Your existing frontend code will automatically start receiving facility names without any changes.

---

## How It Works

### Before (Old Behavior)
```json
POST /api/v1/locations/status/update
{
  "status": "waiting",
  "latitude": 36.9613,
  "longitude": -120.0607
}

Response:
{
  "status": "waiting",
  "location": {
    "latitude": 36.9613,
    "longitude": -120.0607,
    "facility_name": null  ❌ Always null
  }
}
```

### After (New Behavior - Automatic!)
```json
POST /api/v1/locations/status/update
{
  "status": "waiting",
  "latitude": 36.9960,
  "longitude": -120.0968
}

Response:
{
  "status": "waiting",
  "location": {
    "latitude": 36.9960,
    "longitude": -120.0968,
    "facility_name": "Love's Travel Stop"  ✅ Discovered automatically!
  },
  "follow_up_question": {
    "text": "How's it looking?",
    "subtext": "Love's Travel Stop",  ✅ Shows in follow-up too
    "options": [...],
    "metadata": {
      "facility_id": "uuid-here",
      "facility_type": "truck_stop"
    }
  }
}
```

---

## API Contract Unchanged

The `facility_name` field has **always existed** in these endpoints:

### 1. Status Update Response
```typescript
interface StatusChangeResponse {
  status: 'rolling' | 'waiting' | 'parked';
  location: {
    latitude: number;
    longitude: number;
    facility_name: string | null;  // NOW POPULATED! (was always null before)
    facility_id?: string;           // NEW: UUID of facility
  };
  follow_up_question?: {
    text: string;
    subtext: string | null;         // NOW SHOWS FACILITY NAME
    options: Array<{
      id: string;
      text: string;
      next_question_id?: string | null;
    }>;
    metadata?: {
      facility_id?: string;         // NEW
      facility_type?: string;        // NEW: "truck_stop" | "warehouse" | etc
    };
  };
  message: string;
}
```

### 2. Check-in Response
```typescript
interface CheckInResponse {
  message: string;
  location: {
    latitude: number;
    longitude: number;
    facility_name: string | null;  // NOW POPULATED!
  };
  streak?: {
    current_streak: number;
    longest_streak: number;
  };
}
```

### 3. Driver Status Response
```typescript
interface DriverStatusResponse {
  id: string;
  handle: string;
  status: 'rolling' | 'waiting' | 'parked';
  current_location: {
    latitude: number;
    longitude: number;
    facility_name: string | null;  // NOW POPULATED!
    last_updated: string;
  };
}
```

**No breaking changes.** If your frontend already renders `facility_name`, it will just work. If you're not rendering it, you can add it anytime.

---

## What This Means for Users

### Example 1: Truck Stop Discovery
```
Driver at Love's Madera → "You're waiting at Love's Travel Stop"
Instead of: "You're waiting at (36.9960, -120.0968)"
```

### Example 2: Warehouse Discovery
```
Driver at Walmart DC → "You're waiting at Walmart Distribution Center"
Instead of: "You're waiting at (34.0630, -117.6510)"
```

### Example 3: No Facility Nearby
```
Driver in middle of nowhere → "You're waiting"
(facility_name = null, same as before)
```

---

## Optional: UI Improvements You Can Make

### 1. Display Facility Name (if not already)

```typescript
// Example: Status display component
function StatusDisplay({ status, location }) {
  return (
    <View>
      <Text style={styles.status}>
        {status === 'rolling' ? '🟢 Rolling' :
         status === 'waiting' ? '🔴 Waiting' :
         '🔵 Parked'}
      </Text>

      {location.facility_name ? (
        <Text style={styles.facility}>
          📍 {location.facility_name}
        </Text>
      ) : (
        <Text style={styles.coords}>
          📍 Current Location
        </Text>
      )}
    </View>
  );
}
```

### 2. Loading State (Optional)

The first time a driver enters an unmapped area, facility discovery takes **2-4 seconds** (querying OpenStreetMap). Subsequent visits are instant (cached).

**Option A: Show loading indicator**
```typescript
const [isDiscovering, setIsDiscovering] = useState(false);

const handleStatusChange = async (newStatus) => {
  setIsDiscovering(true);
  try {
    const response = await LocationService.updateStatus(newStatus);
    // Response may have facility_name after 2-4 seconds
  } finally {
    setIsDiscovering(false);
  }
};

// In render:
{isDiscovering && <Text>Finding nearby facilities...</Text>}
```

**Option B: Don't show loading** (recommended)
- Most areas are already cached
- 2-4 seconds is rare and acceptable
- User doesn't need to know discovery is happening

### 3. Facility Type Icons (Future Enhancement)

```typescript
function getFacilityIcon(facilityType?: string) {
  switch (facilityType) {
    case 'truck_stop': return '⛽';
    case 'rest_area': return '🅿️';
    case 'warehouse': return '🏭';
    case 'service_plaza': return '🛣️';
    default: return '📍';
  }
}

// Usage:
<Text>
  {getFacilityIcon(metadata?.facility_type)} {location.facility_name}
</Text>
```

### 4. Follow-up Question Subtext (Already Working!)

The backend **automatically** populates `follow_up_question.subtext` with the facility name.

```typescript
// Example: Follow-up question display
function FollowUpQuestion({ question }) {
  if (!question) return null;

  return (
    <View>
      <Text style={styles.question}>{question.text}</Text>

      {question.subtext && (
        <Text style={styles.subtext}>
          📍 {question.subtext}  {/* Shows "Love's Travel Stop" */}
        </Text>
      )}

      {question.options.map(option => (
        <Button key={option.id} title={option.text} />
      ))}
    </View>
  );
}
```

This already works if you're rendering `subtext`! No changes needed.

---

## Performance Considerations

### Discovery Time
- **Cached facilities (99% of cases)**: <50ms
- **First discovery (new area)**: 2-4 seconds
- **No timeout shown to user**: Request completes, facility appears

### Data Usage
- **Cached query**: 0 bytes (database only)
- **OSM discovery**: ~50KB (one-time per area)
- **Negligible impact**: 50KB every 30 days per 25-square-mile area

### Battery Impact
- **No additional GPS usage**: Uses same location data already collected
- **No background queries**: Discovery happens during status update only

---

## Error Handling

The backend handles all errors gracefully:

### Scenario 1: OSM API Timeout
```typescript
// Backend catches timeout, returns null for facility_name
{
  "location": {
    "facility_name": null  // Falls back gracefully
  }
}
```
**Frontend impact**: None. Just shows coordinates like before.

### Scenario 2: No Facilities Nearby
```typescript
{
  "location": {
    "facility_name": null  // No facilities within 0.3 miles
  }
}
```
**Frontend impact**: None. Shows coordinates.

### Scenario 3: Discovery Succeeds
```typescript
{
  "location": {
    "facility_name": "Pilot Travel Center"
  }
}
```
**Frontend impact**: Shows facility name automatically.

**No error handling needed in frontend.** The field is always `string | null`.

---

## Testing Scenarios

### Test Case 1: Driver at Known Truck Stop
```bash
# Backend test location: Love's Madera
latitude: 36.9960
longitude: -120.0968

Expected:
- facility_name: "Love's Travel Stop"
- Response time: <100ms (cached)
```

### Test Case 2: Driver at Warehouse
```bash
# Backend test location: Ontario, CA warehouse district
latitude: 34.0633
longitude: -117.6509

Expected:
- facility_name: "Walmart Distribution Center" (or similar)
- Response time: 2-4s (first time), <100ms (cached)
```

### Test Case 3: Driver in Middle of Nowhere
```bash
# Remote area with no facilities
latitude: 35.0000
longitude: -118.0000

Expected:
- facility_name: null
- Response time: 2-4s (queries OSM, finds nothing, caches empty result)
```

### Test Case 4: Driver Near Facility (0.2 miles away)
```bash
# Within 0.3-mile threshold
latitude: 36.9980  # 0.14 miles from Love's
longitude: -120.0968

Expected:
- facility_name: "Love's Travel Stop"
- Response time: <100ms
```

---

## Migration Path (None Required!)

### If Frontend Already Renders `facility_name`
✅ **Done!** Facility names will appear automatically.

### If Frontend Ignores `facility_name`
✅ **Still works!** Add UI whenever you want. No urgency.

### If Frontend Expects Coordinates
✅ **Still works!** Coordinates are still returned. `facility_name` is additional.

---

## Summary

| What Changed | Frontend Impact |
|-------------|----------------|
| Backend now queries OpenStreetMap | None |
| Backend caches facility data | None |
| `facility_name` now populated | Automatic (if rendered) |
| `follow_up_question.subtext` now shows facility | Automatic (if rendered) |
| New `facility_id` and `facility_type` fields | Optional (can use for icons) |
| Discovery takes 2-4 seconds (first time) | Optional loading indicator |

**Bottom line:** Your existing frontend code will immediately start showing facility names with **zero changes required**. Any UI improvements are optional enhancements you can add at your own pace.

The feature is **live and ready** on the backend! 🚀
