# Weather Integration - Frontend UI Guide

## Apple Weather-Style Animations

This guide shows how to implement beautiful, Apple Weather-style animations for weather alerts in the Find a Truck Driver app.

---

## Overview

When severe weather is detected, the app will show:
1. **Animated weather background** (rain, snow, wind, etc.)
2. **Follow-up question overlay** with weather context
3. **Smooth animations** similar to Apple Weather app

---

## Weather Question Types

The backend returns these weather question types:

| question_type | When Shown | Driver Status |
|--------------|------------|---------------|
| `weather_alert` | Severe/Extreme weather | ROLLING |
| `weather_road_conditions` | Moderate weather | WAITING |
| `weather_stay_safe` | Any weather | PARKED |

---

## Implementation Options

### Option 1: React Native (Recommended)
Use `react-native-weather` or custom animations with `react-native-reanimated`

### Option 2: React Native + Lottie
Use Lottie animations for smooth, vector-based weather effects

### Option 3: Custom Canvas/WebGL
Most complex but most customizable

---

## Recommended: React Native + Lottie Approach

### 1. Install Dependencies

```bash
npm install lottie-react-native
npm install react-native-reanimated
npm install react-native-linear-gradient
```

### 2. Free Lottie Weather Animations

Download from [LottieFiles](https://lottiefiles.com):
- Rain: `rain-animation.json`
- Snow/Blizzard: `snow-animation.json`
- Thunder/Lightning: `thunder-animation.json`
- Wind: `wind-animation.json`
- Tornado: `tornado-animation.json`
- Fog: `fog-animation.json`

---

## Complete Implementation

### TypeScript Interfaces

```typescript
// types/weather.ts

export interface WeatherFollowUpQuestion {
  question_type: 'weather_alert' | 'weather_road_conditions' | 'weather_stay_safe';
  text: string;
  subtext: string;  // Weather headline or summary
  options: FollowUpOption[];
  skippable: boolean;
  auto_dismiss_seconds?: number;

  // Additional context for UI
  weather_event?: string;  // e.g., "Winter Storm Warning"
  weather_emoji?: string;  // e.g., "❄️"
}

export type WeatherAnimationType =
  | 'rain'
  | 'snow'
  | 'thunder'
  | 'wind'
  | 'tornado'
  | 'ice'
  | 'fog'
  | 'heat'
  | 'flood';
```

### Weather Animation Mapper

```typescript
// utils/weatherAnimations.ts

export function getWeatherAnimation(event: string): WeatherAnimationType {
  const eventLower = event.toLowerCase();

  if (eventLower.includes('tornado')) return 'tornado';
  if (eventLower.includes('thunder') || eventLower.includes('lightning')) return 'thunder';
  if (eventLower.includes('snow') || eventLower.includes('blizzard')) return 'snow';
  if (eventLower.includes('ice') || eventLower.includes('freezing')) return 'ice';
  if (eventLower.includes('flood')) return 'flood';
  if (eventLower.includes('wind')) return 'wind';
  if (eventLower.includes('fog')) return 'fog';
  if (eventLower.includes('heat')) return 'heat';
  if (eventLower.includes('rain')) return 'rain';

  return 'rain'; // default
}

export function getWeatherColors(animationType: WeatherAnimationType) {
  switch (animationType) {
    case 'tornado':
      return ['#2C3E50', '#34495E', '#1C2833'];
    case 'thunder':
      return ['#283593', '#3F51B5', '#5C6BC0'];
    case 'snow':
      return ['#E3F2FD', '#BBDEFB', '#90CAF9'];
    case 'ice':
      return ['#B3E5FC', '#81D4FA', '#4FC3F7'];
    case 'flood':
      return ['#1565C0', '#1976D2', '#1E88E5'];
    case 'wind':
      return ['#ECEFF1', '#CFD8DC', '#B0BEC5'];
    case 'fog':
      return ['#ECEFF1', '#CFD8DC', '#90A4AE'];
    case 'heat':
      return ['#FF6F00', '#FF8F00', '#FFA000'];
    case 'rain':
      return ['#37474F', '#455A64', '#546E7A'];
    default:
      return ['#37474F', '#455A64', '#546E7A'];
  }
}
```

### Animated Weather Background Component

```tsx
// components/WeatherBackground.tsx

import React, { useEffect, useRef } from 'react';
import { StyleSheet, View, Dimensions } from 'react-native';
import LottieView from 'lottie-react-native';
import LinearGradient from 'react-native-linear-gradient';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withRepeat,
  withSequence,
} from 'react-native-reanimated';
import { getWeatherColors, WeatherAnimationType } from '../utils/weatherAnimations';

const { width, height } = Dimensions.get('window');

interface WeatherBackgroundProps {
  animationType: WeatherAnimationType;
  intensity?: 'low' | 'medium' | 'high';
}

export function WeatherBackground({ animationType, intensity = 'medium' }: WeatherBackgroundProps) {
  const lottieRef = useRef<LottieView>(null);
  const opacity = useSharedValue(0);

  useEffect(() => {
    // Fade in animation
    opacity.value = withTiming(1, { duration: 800 });
    lottieRef.current?.play();
  }, []);

  // Flash effect for thunder
  const flashOpacity = useSharedValue(0);
  useEffect(() => {
    if (animationType === 'thunder') {
      flashOpacity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 100 }),
          withTiming(0, { duration: 100 }),
          withTiming(0, { duration: 3000 })
        ),
        -1
      );
    }
  }, [animationType]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  const flashStyle = useAnimatedStyle(() => ({
    opacity: flashOpacity.value,
  }));

  const colors = getWeatherColors(animationType);

  return (
    <View style={styles.container}>
      {/* Gradient Background */}
      <LinearGradient
        colors={colors}
        style={styles.gradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
      />

      {/* Lottie Animation */}
      <Animated.View style={[styles.lottieContainer, animatedStyle]}>
        <LottieView
          ref={lottieRef}
          source={getLottieSource(animationType)}
          style={styles.lottie}
          loop
          speed={getAnimationSpeed(intensity)}
        />
      </Animated.View>

      {/* Lightning Flash (for thunder) */}
      {animationType === 'thunder' && (
        <Animated.View style={[styles.flash, flashStyle]} />
      )}
    </View>
  );
}

function getLottieSource(type: WeatherAnimationType) {
  // Map to your Lottie JSON files
  const animations = {
    rain: require('../assets/animations/rain.json'),
    snow: require('../assets/animations/snow.json'),
    thunder: require('../assets/animations/thunder.json'),
    wind: require('../assets/animations/wind.json'),
    tornado: require('../assets/animations/tornado.json'),
    ice: require('../assets/animations/ice.json'),
    fog: require('../assets/animations/fog.json'),
    heat: require('../assets/animations/heat.json'),
    flood: require('../assets/animations/rain.json'), // reuse rain
  };

  return animations[type] || animations.rain;
}

function getAnimationSpeed(intensity: 'low' | 'medium' | 'high'): number {
  switch (intensity) {
    case 'low': return 0.5;
    case 'medium': return 1.0;
    case 'high': return 1.5;
  }
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  gradient: {
    ...StyleSheet.absoluteFillObject,
  },
  lottieContainer: {
    ...StyleSheet.absoluteFillObject,
  },
  lottie: {
    width: width,
    height: height,
  },
  flash: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'white',
  },
});
```

### Weather Alert Modal Component

```tsx
// components/WeatherAlertModal.tsx

import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Platform,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { BlurView } from '@react-native-community/blur';
import { WeatherBackground } from './WeatherBackground';
import { getWeatherAnimation } from '../utils/weatherAnimations';
import type { WeatherFollowUpQuestion, FollowUpOption } from '../types/weather';

const { width } = Dimensions.get('window');

interface WeatherAlertModalProps {
  visible: boolean;
  question: WeatherFollowUpQuestion;
  onRespond: (value: string) => void;
  onDismiss: () => void;
}

export function WeatherAlertModal({
  visible,
  question,
  onRespond,
  onDismiss,
}: WeatherAlertModalProps) {
  const [autoDismissTimer, setAutoDismissTimer] = useState<NodeJS.Timeout | null>(null);
  const scale = useSharedValue(0.8);
  const opacity = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      // Animate in
      scale.value = withSpring(1, {
        damping: 15,
        stiffness: 150,
      });
      opacity.value = withTiming(1, { duration: 300 });

      // Auto-dismiss timer
      if (question.auto_dismiss_seconds) {
        const timer = setTimeout(() => {
          handleDismiss();
        }, question.auto_dismiss_seconds * 1000);
        setAutoDismissTimer(timer);
      }
    } else {
      scale.value = withTiming(0.8, { duration: 200 });
      opacity.value = withTiming(0, { duration: 200 });
    }

    return () => {
      if (autoDismissTimer) clearTimeout(autoDismissTimer);
    };
  }, [visible, question.auto_dismiss_seconds]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  const handleResponse = async (value: string) => {
    if (autoDismissTimer) clearTimeout(autoDismissTimer);
    await onRespond(value);
    handleDismiss();
  };

  const handleDismiss = () => {
    if (autoDismissTimer) clearTimeout(autoDismissTimer);
    onDismiss();
  };

  const animationType = getWeatherAnimation(question.weather_event || question.text);
  const isCritical = question.question_type === 'weather_alert';

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={handleDismiss}
    >
      <View style={styles.modalContainer}>
        {/* Animated Weather Background */}
        <WeatherBackground
          animationType={animationType}
          intensity={isCritical ? 'high' : 'medium'}
        />

        {/* Blur Overlay (iOS only) */}
        {Platform.OS === 'ios' ? (
          <BlurView
            style={styles.blurView}
            blurType="dark"
            blurAmount={20}
          />
        ) : (
          <View style={[styles.blurView, styles.androidOverlay]} />
        )}

        {/* Alert Card */}
        <Animated.View style={[styles.alertCard, animatedStyle]}>
          {/* Critical Badge */}
          {isCritical && (
            <View style={styles.criticalBadge}>
              <Text style={styles.criticalText}>⚠️ SEVERE WEATHER</Text>
            </View>
          )}

          {/* Weather Emoji */}
          <Text style={styles.weatherEmoji}>{question.weather_emoji || '⚠️'}</Text>

          {/* Question Text */}
          <Text style={styles.questionText}>{question.text}</Text>

          {/* Subtext (Weather Headline) */}
          {question.subtext && (
            <Text style={styles.subtext}>{question.subtext}</Text>
          )}

          {/* Options */}
          <View style={styles.optionsContainer}>
            {question.options.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.optionButton,
                  getOptionStyle(option.value, isCritical),
                ]}
                onPress={() => handleResponse(option.value)}
                activeOpacity={0.7}
              >
                <Text style={styles.optionEmoji}>{option.emoji}</Text>
                <Text style={[
                  styles.optionLabel,
                  getOptionTextStyle(option.value, isCritical),
                ]}>
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Skip Button */}
          {question.skippable && (
            <TouchableOpacity
              style={styles.skipButton}
              onPress={handleDismiss}
            >
              <Text style={styles.skipText}>Skip</Text>
            </TouchableOpacity>
          )}

          {/* Auto-dismiss indicator */}
          {question.auto_dismiss_seconds && (
            <Text style={styles.autoDismissText}>
              Auto-dismissing in {question.auto_dismiss_seconds}s
            </Text>
          )}
        </Animated.View>
      </View>
    </Modal>
  );
}

function getOptionStyle(value: string, isCritical: boolean) {
  // Highlight "safe" option in green, "dangerous" in red
  if (value === 'safe' || value === 'acknowledged') {
    return { backgroundColor: '#4CAF50' };
  }
  if (value === 'stopping' || value === 'dangerous') {
    return { backgroundColor: '#F44336' };
  }
  return { backgroundColor: isCritical ? '#FF9800' : '#2196F3' };
}

function getOptionTextStyle(value: string, isCritical: boolean) {
  return { color: 'white', fontWeight: '600' };
}

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  blurView: {
    ...StyleSheet.absoluteFillObject,
  },
  androidOverlay: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  alertCard: {
    width: width * 0.85,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  criticalBadge: {
    position: 'absolute',
    top: -12,
    backgroundColor: '#F44336',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 12,
    shadowColor: '#F44336',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 5,
  },
  criticalText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
  },
  weatherEmoji: {
    fontSize: 64,
    marginTop: 16,
    marginBottom: 12,
  },
  questionText: {
    fontSize: 22,
    fontWeight: '700',
    color: '#1a1a1a',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtext: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  optionsContainer: {
    width: '100%',
    gap: 12,
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 16,
    gap: 8,
  },
  optionEmoji: {
    fontSize: 24,
  },
  optionLabel: {
    fontSize: 16,
  },
  skipButton: {
    marginTop: 16,
    paddingVertical: 8,
  },
  skipText: {
    color: '#999',
    fontSize: 14,
  },
  autoDismissText: {
    marginTop: 12,
    fontSize: 11,
    color: '#999',
    fontStyle: 'italic',
  },
});
```

### Integration in Status Update Flow

```tsx
// screens/StatusUpdateScreen.tsx

import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { WeatherAlertModal } from '../components/WeatherAlertModal';
import { updateDriverStatus, respondToFollowUp } from '../api/status';
import type { WeatherFollowUpQuestion } from '../types/weather';

export function StatusUpdateScreen() {
  const [weatherQuestion, setWeatherQuestion] = useState<WeatherFollowUpQuestion | null>(null);
  const [statusUpdateId, setStatusUpdateId] = useState<string | null>(null);

  async function handleStatusUpdate(status: string, latitude: number, longitude: number) {
    try {
      const response = await updateDriverStatus({
        status,
        latitude,
        longitude,
        accuracy: 10.0,
      });

      // Check for weather follow-up question
      if (response.follow_up_question) {
        const question = response.follow_up_question;

        // Check if it's a weather question
        if (question.question_type.startsWith('weather_')) {
          setWeatherQuestion(question as WeatherFollowUpQuestion);
          setStatusUpdateId(response.status_update_id);
        } else {
          // Handle normal follow-up questions
          // ... your existing logic
        }
      }
    } catch (error) {
      console.error('Status update failed:', error);
    }
  }

  async function handleWeatherResponse(value: string) {
    if (!statusUpdateId) return;

    try {
      const result = await respondToFollowUp(statusUpdateId, value);

      // Log the response for analytics
      console.log('Weather response recorded:', value);

      // Check for status correction
      if (result.status_corrected) {
        // Update local state
        console.log('Status corrected to:', result.new_status);
      }
    } catch (error) {
      console.error('Failed to record weather response:', error);
    }
  }

  return (
    <View style={styles.container}>
      {/* Your status update UI */}

      {/* Weather Alert Modal */}
      <WeatherAlertModal
        visible={weatherQuestion !== null}
        question={weatherQuestion!}
        onRespond={handleWeatherResponse}
        onDismiss={() => setWeatherQuestion(null)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
```

---

## Simpler Alternative: CSS Animations (React Native Web)

If using React Native Web or want lighter animations:

```tsx
// components/SimpleWeatherBackground.tsx

import React from 'react';
import { View, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

export function SimpleWeatherBackground({ type }: { type: string }) {
  return (
    <View style={styles.container}>
      <LinearGradient
        colors={getGradientColors(type)}
        style={styles.gradient}
      >
        {type === 'rain' && <RainEffect />}
        {type === 'snow' && <SnowEffect />}
        {/* Add more effects */}
      </LinearGradient>
    </View>
  );
}

function RainEffect() {
  // Simple rain using animated Views
  return (
    <View style={styles.rainContainer}>
      {[...Array(50)].map((_, i) => (
        <View
          key={i}
          style={[
            styles.raindrop,
            {
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 2}s`,
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
  },
  gradient: {
    flex: 1,
  },
  rainContainer: {
    ...StyleSheet.absoluteFillObject,
  },
  raindrop: {
    position: 'absolute',
    width: 2,
    height: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
    // Add animation here
  },
});
```

---

## Testing Weather UI

### Test with Mock Data

```typescript
// __tests__/WeatherAlert.test.tsx

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { WeatherAlertModal } from '../components/WeatherAlertModal';

const mockWeatherQuestion = {
  question_type: 'weather_alert' as const,
  text: '❄️ Winter Storm Warning',
  subtext: 'Heavy snow expected. Travel may become dangerous.',
  options: [
    { emoji: '👍', label: "I'm safe", value: 'safe' },
    { emoji: '⚠️', label: 'Pulling over', value: 'stopping' },
  ],
  skippable: true,
  weather_event: 'Winter Storm Warning',
  weather_emoji: '❄️',
};

test('renders weather alert modal', () => {
  const { getByText } = render(
    <WeatherAlertModal
      visible={true}
      question={mockWeatherQuestion}
      onRespond={jest.fn()}
      onDismiss={jest.fn()}
    />
  );

  expect(getByText('❄️ Winter Storm Warning')).toBeTruthy();
  expect(getByText("I'm safe")).toBeTruthy();
});
```

---

## Resources

### Free Lottie Animations
- [LottieFiles - Weather](https://lottiefiles.com/search?q=weather&category=animations)
- [IconScout - Weather Animations](https://iconscout.com/lottie-animations/weather)

### Libraries
- [react-native-reanimated](https://docs.swmansion.com/react-native-reanimated/)
- [lottie-react-native](https://github.com/lottie-react-native/lottie-react-native)
- [react-native-linear-gradient](https://github.com/react-native-linear-gradient/react-native-linear-gradient)
- [react-native-blur](https://github.com/Kureev/react-native-blur)

---

## Summary

**Frontend needs to**:
1. ✅ Detect `weather_*` question types from status update response
2. ✅ Show animated weather background (Lottie recommended)
3. ✅ Display alert modal with Apple Weather-style design
4. ✅ Handle user responses via `/api/v1/follow-ups/respond`
5. ✅ Support auto-dismiss for non-critical alerts
6. ✅ Use appropriate colors/animations based on weather type

The backend is already complete and returning weather questions! 🎉
