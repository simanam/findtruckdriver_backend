# Profile Management - Quick Reference

## Available APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/drivers/me` | GET | ✅ | Get full profile |
| `/drivers/me/stats` | GET | ✅ | Get statistics |
| `/drivers/me/profile` | PATCH | ✅ | Update avatar/handle |
| `/drivers/me` | DELETE | ✅ | Delete account |

---

## Common Use Cases

### 1. Load Profile Page

```typescript
const { profile, stats } = await Promise.all([
  api.get('/drivers/me'),
  api.get('/drivers/me/stats')
]);

// Display:
// - Avatar
// - Handle (@username)
// - Member for X days
// - Total updates: 342
// - Rolling: 156, Waiting: 89, Parked: 97
```

### 2. Change Avatar

```typescript
await api.patch('/drivers/me/profile', {
  avatar_id: 'avatar_42'
});
```

### 3. Change Handle

```typescript
try {
  await api.patch('/drivers/me/profile', {
    handle: 'new_username'
  });
} catch (error) {
  if (error.status === 400) {
    // Handle already taken
  }
}
```

### 4. Delete Account

```typescript
await api.delete('/drivers/me', {
  confirmation: 'DELETE',
  reason: 'Optional reason here'
});

// Then clear tokens and redirect to login
```

---

## Response Examples

### Profile
```json
{
  "id": "...",
  "handle": "bigrig_mike",
  "avatar_id": "avatar_12",
  "status": "parked",
  "last_active": "2026-01-09T10:30:00Z",
  "created_at": "2025-12-01T08:00:00Z"
}
```

### Stats
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

---

## Validation Rules

### Handle
- 3-30 characters
- Alphanumeric + underscores + hyphens only
- Must be unique
- Automatically lowercased

### Account Deletion
- Confirmation must be exactly "DELETE" (uppercase)
- Reason is optional (max 500 chars)
- Irreversible - all data deleted

---

## What Gets Deleted

When user deletes account:
1. ✅ Driver profile
2. ✅ All status updates
3. ✅ All location data
4. ✅ Follow-up responses
5. ✅ Supabase Auth account

**Cannot be recovered!**
