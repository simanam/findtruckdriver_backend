# Frontend Integration Guide: Follow-Up Questions Edge Cases

## Quick Start: What Frontend Needs to Do

### **TL;DR: Almost Nothing! But Optional Enhancements Available**

The follow-up question system is **backend-driven** and works automatically with minimal frontend changes. However, there are **optional enhancements** that improve UX.

---

## Required Changes: None ✅

### Existing API Contract Still Works

```typescript
interface StatusUpdateResponse {
  status: 'rolling' | 'waiting' | 'parked';
  location: {
    latitude: number;
    longitude: number;
    facility_name?: string;
  };
  follow_up_question?: FollowUpQuestion;  // This field already exists!
  message: string;
}
```

**If your frontend already displays `follow_up_question`, it will automatically show all the new edge case questions!**

---

## Optional Enhancement #1: Status Correction (Recommended)

### What's New?

When users select "Still waiting" on the "Calling it a night?" question, the backend automatically corrects their status back to WAITING.

### API Response (New Field)

```typescript
interface FollowUpResponseResult {
  success: boolean;
  message: string;
  status_update_id: string;
  status_corrected?: boolean;  // ⭐ NEW!
  new_status?: string;          // ⭐ NEW!
}
```

### Frontend Implementation

```typescript
// In your follow-up response handler
async function handleFollowUpResponse(
  statusUpdateId: string,
  responseValue: string
) {
  try {
    const result = await api.post('/api/v1/follow-ups/respond', {
      status_update_id: statusUpdateId,
      response_value: responseValue
    });

    // ⭐ NEW: Check for status correction
    if (result.status_corrected) {
      // Update local state
      setCurrentStatus(result.new_status);

      // Show user feedback
      showToast(`Status corrected to ${result.new_status.toUpperCase()}`);

      // Optional: Refresh driver info
      await refreshDriverStatus();
    }

    // Hide the question
    setFollowUpQuestion(null);

  } catch (error) {
    console.error('Failed to submit follow-up response:', error);
    showError('Failed to submit response');
  }
}
```

### React Example

```tsx
function FollowUpQuestionCard({
  question,
  statusUpdateId,
  onStatusCorrected
}: {
  question: FollowUpQuestion;
  statusUpdateId: string;
  onStatusCorrected?: (newStatus: string) => void;
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleOptionSelect(value: string) {
    setIsSubmitting(true);

    try {
      const response = await api.followUps.respond(statusUpdateId, value);

      // ⭐ Handle status correction
      if (response.status_corrected && onStatusCorrected) {
        onStatusCorrected(response.new_status);

        // Show success message
        Toast.show({
          type: 'success',
          text1: 'Status Corrected',
          text2: `Changed back to ${response.new_status.toUpperCase()}`
        });
      }

    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Failed to submit response'
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card style={styles.card}>
      <Text style={styles.question}>{question.text}</Text>

      {question.subtext && (
        <Text style={styles.subtext}>{question.subtext}</Text>
      )}

      <View style={styles.options}>
        {question.options.map(option => (
          <TouchableOpacity
            key={option.value}
            style={styles.optionButton}
            onPress={() => handleOptionSelect(option.value)}
            disabled={isSubmitting}
          >
            <Text style={styles.optionEmoji}>{option.emoji}</Text>
            <Text style={styles.optionLabel}>{option.label}</Text>

            {option.description && (
              <Text style={styles.optionDescription}>
                {option.description}
              </Text>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {question.skippable && (
        <Button
          variant="ghost"
          onPress={() => handleOptionSelect('skipped')}
          disabled={isSubmitting}
        >
          Skip
        </Button>
      )}
    </Card>
  );
}
```

---

## Optional Enhancement #2: Auto-Dismiss (Recommended)

### What's New?

Some questions auto-dismiss after a few seconds (acknowledgments, encouragement messages).

### New Field in Question

```typescript
interface FollowUpQuestion {
  question_type: string;
  text: string;
  subtext?: string;
  options: FollowUpOption[];
  skippable: boolean;
  auto_dismiss_seconds?: number;  // ⭐ NEW!
}
```

### Frontend Implementation

```tsx
function FollowUpQuestionCard({ question, statusUpdateId }) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // ⭐ Auto-dismiss timer
    if (question.auto_dismiss_seconds && !dismissed) {
      const timer = setTimeout(() => {
        setDismissed(true);
        // Optionally auto-select first option
        if (question.options[0]) {
          handleOptionSelect(question.options[0].value);
        }
      }, question.auto_dismiss_seconds * 1000);

      return () => clearTimeout(timer);
    }
  }, [question, dismissed]);

  if (dismissed) return null;

  return (
    <Card>
      {/* Question UI */}
      {question.auto_dismiss_seconds && (
        <Text style={styles.autoDismissHint}>
          Auto-dismissing in {question.auto_dismiss_seconds}s...
        </Text>
      )}
    </Card>
  );
}
```

---

## Optional Enhancement #3: Display Subtext (Recommended)

### What's New?

Questions now include contextual subtexts (facility names, wait durations, etc.)

### Example Subtexts

- "Love's Travel Stop" (facility name)
- "3 hrs" (wait duration)
- "Sysco Foodservice" (facility context)

### Frontend Implementation

```tsx
{question.subtext && (
  <View style={styles.subtextContainer}>
    <Icon name="location" size={14} color="#666" />
    <Text style={styles.subtext}>{question.subtext}</Text>
  </View>
)}
```

### Styling Example

```typescript
const styles = StyleSheet.create({
  question: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginBottom: 8
  },
  subtextContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16
  },
  subtext: {
    fontSize: 14,
    color: '#666',
    marginLeft: 4
  }
});
```

---

## Optional Enhancement #4: Option Descriptions (Nice to Have)

### What's New?

Some options include helpful descriptions (tips for first-time users).

### New Field in Option

```typescript
interface FollowUpOption {
  emoji: string;
  label: string;
  value: string;
  description?: string;  // ⭐ NEW!
}
```

### Frontend Implementation

```tsx
{question.options.map(option => (
  <TouchableOpacity key={option.value} style={styles.option}>
    <Text style={styles.emoji}>{option.emoji}</Text>
    <View style={styles.labelContainer}>
      <Text style={styles.label}>{option.label}</Text>

      {/* ⭐ Show description if available */}
      {option.description && (
        <Text style={styles.description}>{option.description}</Text>
      )}
    </View>
  </TouchableOpacity>
))}
```

---

## Complete Example: Full Integration

### TypeScript Types

```typescript
interface FollowUpOption {
  emoji: string;
  label: string;
  value: string;
  description?: string;
}

interface FollowUpQuestion {
  question_type: string;
  text: string;
  subtext?: string;
  options: FollowUpOption[];
  skippable: boolean;
  auto_dismiss_seconds?: number;
}

interface StatusUpdateResponse {
  status: string;
  location: {
    latitude: number;
    longitude: number;
    facility_name?: string;
  };
  follow_up_question?: FollowUpQuestion;
  message: string;
}

interface FollowUpResponseResult {
  success: boolean;
  message: string;
  status_update_id: string;
  status_corrected?: boolean;
  new_status?: string;
}
```

### Complete React Component

```tsx
import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Card } from '@/components/ui/Card';
import { Toast } from '@/services/toast';
import { api } from '@/services/api';

interface FollowUpQuestionCardProps {
  question: FollowUpQuestion;
  statusUpdateId: string;
  onDismiss: () => void;
  onStatusCorrected?: (newStatus: string) => void;
}

export function FollowUpQuestionCard({
  question,
  statusUpdateId,
  onDismiss,
  onStatusCorrected
}: FollowUpQuestionCardProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [countdown, setCountdown] = useState(
    question.auto_dismiss_seconds || 0
  );

  // Auto-dismiss countdown
  useEffect(() => {
    if (question.auto_dismiss_seconds && countdown > 0 && !dismissed) {
      const timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }

    // Auto-dismiss when countdown reaches 0
    if (countdown === 0 && question.auto_dismiss_seconds && !dismissed) {
      handleAutoSelect();
    }
  }, [countdown, dismissed, question]);

  async function handleAutoSelect() {
    if (question.options[0]) {
      await handleOptionSelect(question.options[0].value);
    }
    setDismissed(true);
    onDismiss();
  }

  async function handleOptionSelect(value: string) {
    if (isSubmitting) return;

    setIsSubmitting(true);

    try {
      const response = await api.post<FollowUpResponseResult>(
        '/api/v1/follow-ups/respond',
        {
          status_update_id: statusUpdateId,
          response_value: value
        }
      );

      // Handle status correction
      if (response.status_corrected && onStatusCorrected) {
        onStatusCorrected(response.new_status!);

        Toast.show({
          type: 'success',
          text1: 'Status Corrected',
          text2: `Changed back to ${response.new_status!.toUpperCase()}`,
          position: 'top'
        });
      }

      // Dismiss the question
      setDismissed(true);
      onDismiss();

    } catch (error) {
      console.error('Failed to submit follow-up response:', error);
      Toast.show({
        type: 'error',
        text1: 'Failed to submit response',
        text2: 'Please try again',
        position: 'top'
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSkip() {
    setDismissed(true);
    onDismiss();
  }

  if (dismissed) return null;

  return (
    <Card style={styles.card}>
      {/* Question Text */}
      <Text style={styles.question}>{question.text}</Text>

      {/* Subtext (facility name, duration, etc.) */}
      {question.subtext && (
        <View style={styles.subtextContainer}>
          <Text style={styles.subtext}>{question.subtext}</Text>
        </View>
      )}

      {/* Auto-dismiss countdown */}
      {question.auto_dismiss_seconds && countdown > 0 && (
        <Text style={styles.countdown}>
          Auto-dismissing in {countdown}s...
        </Text>
      )}

      {/* Options */}
      <View style={styles.options}>
        {question.options.map(option => (
          <TouchableOpacity
            key={option.value}
            style={[
              styles.optionButton,
              isSubmitting && styles.optionButtonDisabled
            ]}
            onPress={() => handleOptionSelect(option.value)}
            disabled={isSubmitting}
            activeOpacity={0.7}
          >
            <Text style={styles.optionEmoji}>{option.emoji}</Text>
            <View style={styles.optionTextContainer}>
              <Text style={styles.optionLabel}>{option.label}</Text>

              {/* Option description (for first-time users) */}
              {option.description && (
                <Text style={styles.optionDescription}>
                  {option.description}
                </Text>
              )}
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* Skip button */}
      {question.skippable && (
        <TouchableOpacity
          style={styles.skipButton}
          onPress={handleSkip}
          disabled={isSubmitting}
        >
          <Text style={styles.skipText}>Skip</Text>
        </TouchableOpacity>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 12,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3
  },
  question: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginBottom: 8
  },
  subtextContainer: {
    marginBottom: 12
  },
  subtext: {
    fontSize: 14,
    color: '#666'
  },
  countdown: {
    fontSize: 12,
    color: '#999',
    marginBottom: 12,
    fontStyle: 'italic'
  },
  options: {
    gap: 8,
    marginBottom: 12
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0'
  },
  optionButtonDisabled: {
    opacity: 0.5
  },
  optionEmoji: {
    fontSize: 24,
    marginRight: 12
  },
  optionTextContainer: {
    flex: 1
  },
  optionLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#000'
  },
  optionDescription: {
    fontSize: 12,
    color: '#666',
    marginTop: 4
  },
  skipButton: {
    padding: 8,
    alignItems: 'center'
  },
  skipText: {
    fontSize: 14,
    color: '#999',
    textDecorationLine: 'underline'
  }
});
```

### Usage in Status Update Screen

```tsx
function StatusUpdateScreen() {
  const [currentStatus, setCurrentStatus] = useState<string>('rolling');
  const [followUpQuestion, setFollowUpQuestion] = useState<FollowUpQuestion | null>(null);
  const [statusUpdateId, setStatusUpdateId] = useState<string | null>(null);

  async function handleStatusChange(newStatus: string) {
    try {
      const response = await api.post<StatusUpdateResponse>(
        '/api/v1/locations/status/update',
        {
          status: newStatus,
          latitude: currentLocation.latitude,
          longitude: currentLocation.longitude,
          accuracy: 10.0
        }
      );

      // Update local state
      setCurrentStatus(response.status);

      // Show follow-up question if present
      if (response.follow_up_question) {
        setFollowUpQuestion(response.follow_up_question);
        setStatusUpdateId(response.status_update_id);
      }

    } catch (error) {
      console.error('Failed to update status:', error);
    }
  }

  function handleStatusCorrected(newStatus: string) {
    // Update local state after status correction
    setCurrentStatus(newStatus);
  }

  return (
    <View>
      {/* Status buttons */}
      <StatusButtons
        currentStatus={currentStatus}
        onStatusChange={handleStatusChange}
      />

      {/* Follow-up question */}
      {followUpQuestion && statusUpdateId && (
        <FollowUpQuestionCard
          question={followUpQuestion}
          statusUpdateId={statusUpdateId}
          onDismiss={() => setFollowUpQuestion(null)}
          onStatusCorrected={handleStatusCorrected}
        />
      )}
    </View>
  );
}
```

---

## Question Types Reference

Here are all 24 question types your frontend might receive:

| question_type | When Shown | Auto-Dismiss |
|--------------|------------|--------------|
| `first_time_parked` | First status update ever (PARKED) | No |
| `first_time_waiting` | First status update ever (WAITING) | No |
| `first_time_rolling` | First status update ever (ROLLING) | 3 seconds |
| `returning_parked` | After 24+ hours away (PARKED) | No |
| `returning_waiting` | After 24+ hours away (WAITING) | No |
| `returning_rolling` | After 24+ hours away (ROLLING) | 3 seconds |
| `checkin_parked_short` | Same PARKED status < 2 hours | 2 seconds |
| `checkin_parked_long` | Same PARKED status 2+ hours | No |
| `checkin_waiting` | Same WAITING status | No |
| `checkin_rolling` | Same ROLLING status | 1 second |
| `parking_spot_entry` | → PARKED (normal) | No |
| `facility_flow_entry` | → WAITING (normal) | No |
| `drive_safe` | → ROLLING (normal) | 2 seconds |
| `quick_turnaround` | WAITING → ROLLING < 1 hour | 2 seconds |
| `normal_turnaround` | WAITING → ROLLING 1-2 hours | 2 seconds |
| `detention_payment` | WAITING → ROLLING 2-4 hours | No |
| `detention_payment_brutal` | WAITING → ROLLING 4+ hours | No |
| **`calling_it_a_night`** | **WAITING → PARKED same location** | **No** (Status correction!) |
| `done_at_facility_detention` | WAITING → PARKED nearby 2+ hours | No |
| `time_to_work` | PARKED → WAITING | No |

**⚠️ Special**: `calling_it_a_night` with "Still waiting" response triggers status correction!

---

## Testing Checklist

### Manual Testing Scenarios

1. **First-Time User**
   - Create new account
   - Set status to PARKED
   - ✓ See "Welcome to Find a Truck Driver! 🚛"
   - ✓ See helpful description on options

2. **Status Correction**
   - Status WAITING for 2 hours
   - Change to PARKED (same location)
   - ✓ See "Calling it a night?"
   - Select "Still waiting"
   - ✓ Status automatically changes back to WAITING
   - ✓ Toast shows "Status corrected to WAITING"

3. **Auto-Dismiss**
   - Status ROLLING
   - Check in (same status, same location)
   - ✓ See "✓ Location updated"
   - ✓ Auto-dismisses after 1 second
   - ✓ Countdown shows (optional)

4. **Detention Tracking**
   - Status WAITING for 3 hours
   - Change to ROLLING
   - ✓ See "3 hrs. Getting paid?"
   - ✓ Duration shown in subtext
   - Select "Yep" or "Nope"
   - ✓ Response recorded

5. **Returning User**
   - Don't use app for 2 days
   - Open app and set status
   - ✓ See "Back at it! Been 2 days"
   - ✓ See appropriate follow-up question

---

## API Endpoints Summary

### Status Update
```http
POST /api/v1/locations/status/update
Authorization: Bearer <token>

Request:
{
  "status": "parked",
  "latitude": 36.9960,
  "longitude": -120.0968,
  "accuracy": 10.0
}

Response:
{
  "status": "parked",
  "location": { ... },
  "follow_up_question": { ... }  // May be null
}
```

### Follow-Up Response
```http
POST /api/v1/follow-ups/respond
Authorization: Bearer <token>

Request:
{
  "status_update_id": "uuid",
  "response_value": "solid"
}

Response:
{
  "success": true,
  "message": "Response recorded successfully",
  "status_update_id": "uuid",
  "status_corrected": false  // true if status was corrected
}
```

---

## Migration Guide

### If You Already Display Follow-Up Questions

✅ **You're done!** New questions will automatically appear.

**Optional improvements**:
1. Handle `status_corrected` field (10 min)
2. Implement auto-dismiss timer (15 min)
3. Display `subtext` field (5 min)
4. Show option descriptions (5 min)

**Total time**: ~35 minutes for all enhancements

### If You Don't Display Follow-Up Questions Yet

Implement the complete component above (~2-3 hours for first-time implementation).

---

## Support & Documentation

- **Quick Reference**: [FOLLOW_UP_QUICK_REFERENCE.md](FOLLOW_UP_QUICK_REFERENCE.md)
- **Complete Summary**: [EDGE_CASES_COMPLETE_SUMMARY.md](EDGE_CASES_COMPLETE_SUMMARY.md)
- **Backend Details**: [PHASE1_EDGE_CASES_COMPLETE.md](PHASE1_EDGE_CASES_COMPLETE.md) & [PHASE2_EDGE_CASES_COMPLETE.md](PHASE2_EDGE_CASES_COMPLETE.md)

---

## Summary: What Frontend Should Implement

### Priority 1: Required (Already Works)
- ✅ Display `follow_up_question` if present
- ✅ Submit response to `/follow-ups/respond`
- ✅ Handle null/missing questions gracefully

### Priority 2: Highly Recommended
- ⭐ Handle `status_corrected` response field
- ⭐ Implement auto-dismiss timer
- ⭐ Display `subtext` for context

### Priority 3: Nice to Have
- 💡 Show option descriptions (first-time users)
- 💡 Countdown animation for auto-dismiss
- 💡 Haptic feedback on selection
- 💡 Accessibility labels

**Bottom Line**: The system works out of the box. Enhancements make it even better! 🚀
