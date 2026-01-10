# Profile Management API

Complete guide to driver profile management endpoints.

---

## Overview

The profile management system allows drivers to:
- View their profile and statistics
- Update avatar and handle
- Delete their account and all data

All endpoints require authentication unless specified.

---

## Endpoints

### 1. Get My Profile

**Endpoint**: `GET /api/v1/drivers/me`

**Authentication**: ✅ Required

**Description**: Get current driver's full profile

**Response**:
```json
{
  "id": "7dc28bb5-9112-4856-82d1-c973e045368d",
  "user_id": "abc123-def456-...",
  "handle": "bigrig_mike",
  "avatar_id": "avatar_12",
  "status": "parked",
  "last_active": "2026-01-09T10:30:00Z",
  "created_at": "2025-12-01T08:00:00Z"
}
```

---

### 2. Get My Statistics

**Endpoint**: `GET /api/v1/drivers/me/stats`

**Authentication**: ✅ Required

**Description**: Get driver profile statistics including total updates, days active, and status breakdown

**Response**:
```json
{
  "total_status_updates": 342,
  "days_active": 40,
  "rolling_count": 156,
  "waiting_count": 89,
  "parked_count": 97,
  "member_since": "2025-12-01T08:00:00Z",
  "last_active": "2026-01-09T10:30:00Z"
}
```

**Use Cases**:
- Display profile stats on profile page
- Show "Days on the road" badge
- Activity breakdown charts

---

### 3. Update Profile (Avatar & Handle)

**Endpoint**: `PATCH /api/v1/drivers/me/profile`

**Authentication**: ✅ Required

**Description**: Update driver profile information (handle and avatar only). Status updates use a different endpoint.

**Request Body**:
```json
{
  "handle": "new_handle",
  "avatar_id": "avatar_42"
}
```

**Fields** (all optional):
- `handle` (string, 3-30 chars): New unique handle
- `avatar_id` (string): New avatar identifier

**Response** (full driver profile):
```json
{
  "id": "7dc28bb5-9112-4856-82d1-c973e045368d",
  "user_id": "abc123-def456-...",
  "handle": "new_handle",
  "avatar_id": "avatar_42",
  "status": "parked",
  "last_active": "2026-01-09T10:30:00Z",
  "created_at": "2025-12-01T08:00:00Z"
}
```

**Errors**:
- `400 Bad Request`: Handle already taken
- `400 Bad Request`: Invalid handle format (must be alphanumeric with _ or -)

**Example - Update Avatar Only**:
```json
{
  "avatar_id": "avatar_99"
}
```

**Example - Update Handle Only**:
```json
{
  "handle": "highway_hero"
}
```

---

### 4. Delete Account

**Endpoint**: `DELETE /api/v1/drivers/me`

**Authentication**: ✅ Required

**Description**: Permanently delete driver account and all associated data.

**⚠️ Warning**: This is a destructive operation that cannot be undone!

**What Gets Deleted**:
1. Driver profile
2. All status updates
3. All location data
4. Follow-up responses
5. Authentication account (Supabase Auth)

**Request Body**:
```json
{
  "confirmation": "DELETE",
  "reason": "No longer driving trucks"
}
```

**Fields**:
- `confirmation` (string, required): Must be exactly "DELETE"
- `reason` (string, optional, max 500 chars): Reason for deletion

**Response**:
```json
{
  "success": true,
  "message": "Account successfully deleted",
  "deleted_at": "2026-01-09T10:35:00Z"
}
```

**Errors**:
- `400 Bad Request`: Confirmation not "DELETE"
- `500 Internal Server Error`: Deletion failed

**Important Notes**:
- Frontend should clear local tokens after successful deletion
- User will need to re-authenticate if they want to create a new account
- Deletion is logged with reason for analytics

---

## Frontend Integration

### Profile Page Example

```typescript
// Get profile and stats
async function loadProfilePage() {
  const [profile, stats] = await Promise.all([
    api.get('/drivers/me'),
    api.get('/drivers/me/stats')
  ]);

  return { profile, stats };
}

// Display stats
function ProfileStats({ stats }) {
  return (
    <View>
      <Text>Member for {stats.days_active} days</Text>
      <Text>Total Updates: {stats.total_status_updates}</Text>
      <Text>Rolling: {stats.rolling_count}</Text>
      <Text>Waiting: {stats.waiting_count}</Text>
      <Text>Parked: {stats.parked_count}</Text>
    </View>
  );
}
```

### Avatar Change

```typescript
async function changeAvatar(newAvatarId: string) {
  const response = await api.patch('/drivers/me/profile', {
    avatar_id: newAvatarId
  });

  // Update local state
  setProfile(response);
}
```

### Handle Change

```typescript
async function changeHandle(newHandle: string) {
  try {
    const response = await api.patch('/drivers/me/profile', {
      handle: newHandle
    });

    toast.success(`Handle changed to @${newHandle}`);
    setProfile(response);
  } catch (error) {
    if (error.status === 400) {
      toast.error('Handle already taken');
    }
  }
}
```

### Account Deletion Flow

```typescript
async function deleteAccount(reason?: string) {
  // Show confirmation dialog
  const confirmed = await showDialog({
    title: 'Delete Account?',
    message: 'This will permanently delete all your data. Type DELETE to confirm.',
    input: true
  });

  if (confirmed !== 'DELETE') {
    return;
  }

  try {
    await api.delete('/drivers/me', {
      confirmation: 'DELETE',
      reason: reason
    });

    // Clear local storage
    await clearTokens();

    // Navigate to goodbye screen
    navigation.navigate('AccountDeleted');
  } catch (error) {
    toast.error('Failed to delete account');
  }
}
```

---

## UI/UX Recommendations

### Profile Page Layout

```
┌─────────────────────────────────┐
│  [Avatar]  @handle              │
│                                 │
│  Member for 40 days             │
│  Last active: 2 hours ago       │
├─────────────────────────────────┤
│  STATISTICS                     │
│  Total Updates: 342             │
│  🚛 Rolling: 156                │
│  ⏱️  Waiting: 89                │
│  🅿️  Parked: 97                 │
├─────────────────────────────────┤
│  SETTINGS                       │
│  > Change Avatar                │
│  > Change Handle                │
│  > Delete Account (red)         │
└─────────────────────────────────┘
```

### Avatar Picker

- Show grid of available avatars
- Highlight current avatar
- Update instantly on selection
- Show success toast

### Handle Editor

- Show availability check as user types
- Real-time validation (alphanumeric + _ -)
- Show "Handle taken" error inline
- Confirm button only enabled when valid

### Account Deletion

**Step 1**: Tap "Delete Account"
```
⚠️ Warning
This will permanently delete:
- Your profile
- All status updates
- Location history
- Everything

[Cancel] [Continue]
```

**Step 2**: Type confirmation
```
Type DELETE to confirm
[________]

Why are you leaving? (optional)
[Reason text area]

[Cancel] [Delete Forever]
```

**Step 3**: Farewell screen
```
Account Deleted

Your data has been permanently removed.
Thanks for using FindTruckDriver.

[Close App]
```

---

## Security Considerations

### Handle Changes
- Validate handle uniqueness server-side
- Rate limit handle changes (max 1 per day?)
- Log handle changes for moderation

### Account Deletion
- Require explicit "DELETE" confirmation
- Log deletion with reason for analytics
- Consider soft delete (mark as deleted, purge after 30 days)?
- Email confirmation option for added security

### Data Privacy
- GDPR compliance: User can delete all data
- Consider data export feature (download JSON)
- Clear all sessions on account deletion

---

## Analytics to Track

```typescript
// Profile views
analytics.track('profile_viewed', {
  driver_id: driverId
});

// Avatar changes
analytics.track('avatar_changed', {
  driver_id: driverId,
  old_avatar: oldAvatarId,
  new_avatar: newAvatarId
});

// Handle changes
analytics.track('handle_changed', {
  driver_id: driverId,
  old_handle: oldHandle,
  new_handle: newHandle
});

// Account deletions
analytics.track('account_deleted', {
  driver_id: driverId,
  reason: reason,
  days_active: stats.days_active,
  total_updates: stats.total_status_updates
});
```

---

## Testing Checklist

### Profile Retrieval
- [ ] Get profile returns correct data
- [ ] Stats calculation is accurate
- [ ] Unauthorized request returns 401

### Profile Updates
- [ ] Avatar change works
- [ ] Handle change works
- [ ] Handle uniqueness enforced
- [ ] Invalid handle format rejected
- [ ] Can update both fields at once
- [ ] Can update one field only

### Account Deletion
- [ ] Requires "DELETE" confirmation
- [ ] Deletes all driver data
- [ ] Deletes all status updates
- [ ] Deletes all location data
- [ ] Deletes auth account
- [ ] Returns success message
- [ ] Logs deletion reason

---

## Future Enhancements

### Profile Customization
- [ ] Profile bio/tagline
- [ ] Preferred routes
- [ ] Truck type/company
- [ ] Years of experience

### Privacy Settings
- [ ] Profile visibility (public/private)
- [ ] Hide location from other drivers
- [ ] Anonymous mode

### Data Portability
- [ ] Export all data as JSON
- [ ] GDPR compliance
- [ ] Download status update history

### Account Recovery
- [ ] Soft delete (30-day grace period)
- [ ] Account deactivation (temporary)
- [ ] Reactivation flow

---

## Summary

**Available Endpoints**:
1. `GET /drivers/me` - Get profile
2. `GET /drivers/me/stats` - Get statistics
3. `PATCH /drivers/me/profile` - Update avatar/handle
4. `DELETE /drivers/me` - Delete account

**What Drivers Can Do**:
- ✅ View profile and stats
- ✅ Change avatar
- ✅ Change handle (username)
- ✅ Delete account permanently

**What's Protected**:
- Handle uniqueness enforced
- Account deletion requires confirmation
- All data deleted on account removal
- Deletion logged for analytics

🎯 **Complete profile management ready for frontend integration!**
