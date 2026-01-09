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
