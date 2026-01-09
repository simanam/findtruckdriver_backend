# Supabase Keys Explained

## TL;DR: You Need BOTH Keys

✅ **SUPABASE_PUBLISHABLE_KEY** - For client operations (frontend)
✅ **SUPABASE_SERVICE_KEY** - For server operations (backend API)

---

## The Two Keys

### 1. SUPABASE_PUBLISHABLE_KEY (formerly "anon key")

**Where to find it**: Supabase Dashboard → Project Settings → API → "Project API keys" → `publishable key`

**Purpose**: Client-side operations with Row Level Security enforced

**Characteristics**:
- ✅ Safe to expose in frontend code
- ✅ Subject to Row Level Security (RLS) policies
- ✅ Users can only access data allowed by RLS
- ✅ Used for authenticated user operations

**Use cases**:
- Frontend authentication
- User-specific queries
- Operations that respect RLS policies
- Mobile app API calls

**Example**:
```javascript
// Frontend (safe to expose)
const supabase = createClient(
  'https://xxx.supabase.co',
  'eyJhbGc...publishable_key_here'  // ✅ OK in frontend
)
```

---

### 2. SUPABASE_SERVICE_KEY (service_role key)

**Where to find it**: Supabase Dashboard → Project Settings → API → "Project API keys" → `service_role` (secret)

**Purpose**: Server-side admin operations that bypass RLS

**Characteristics**:
- 🔒 **NEVER expose in frontend** - only use server-side
- 🔒 Bypasses ALL Row Level Security policies
- 🔒 Full admin access to database
- 🔒 Can read/write any data regardless of RLS

**Use cases**:
- Backend API operations
- Admin tasks (bulk updates, cleanup jobs)
- System operations (stats aggregation, hotspot detection)
- Operations that need to query across all users

**Example**:
```python
# Backend ONLY (never expose)
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]  # 🔒 Server-side only
)
```

---

## Why We Need Both in This Project

### Backend Uses SERVICE_KEY

Our FastAPI backend needs the **SERVICE_KEY** because:

1. **Stats Aggregation**: Count all drivers across regions (bypasses RLS)
2. **Map Data**: Return aggregated driver data for all zoom levels
3. **Hotspot Detection**: Analyze clusters of waiting drivers system-wide
4. **Admin Operations**: Create/update facilities, cleanup old data
5. **System Health**: Monitor inactive drivers, calculate averages

Example operations requiring SERVICE_KEY:
```python
# Get ALL active drivers for map view (needs to bypass RLS)
drivers = supabase.from_("drivers") \
    .select("*") \
    .gte("last_active", thirty_mins_ago) \
    .execute()  # Returns all drivers (admin access)
```

### Frontend Uses PUBLISHABLE_KEY

The Next.js frontend uses **PUBLISHABLE_KEY** because:

1. **User Authentication**: Sign in/sign up flows
2. **Profile Updates**: User updating their own status/location
3. **Personal Data**: Fetching their own driver record
4. **Security**: RLS ensures users can't access others' sensitive data

Example operations using PUBLISHABLE_KEY:
```typescript
// User can only update their OWN profile (RLS enforced)
const { data } = await supabase
  .from('drivers')
  .update({ status: 'rolling' })
  .eq('user_id', user.id)  // ✅ RLS ensures this matches auth.uid()
```

---

## Security Best Practices

### ✅ DO:
- Store SERVICE_KEY in `.env` (never commit)
- Use SERVICE_KEY only in backend code
- Use PUBLISHABLE_KEY in frontend
- Keep `.env` in `.gitignore`
- Rotate keys if compromised

### ❌ DON'T:
- Expose SERVICE_KEY in frontend/mobile apps
- Commit SERVICE_KEY to Git
- Use SERVICE_KEY in client-side JavaScript
- Share SERVICE_KEY in public documentation
- Hardcode keys in source code

---

## Finding Your Keys

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click **Project Settings** (cog icon)
4. Go to **API** section
5. Copy both keys:
   - **Project API keys** → `publishable` → Copy
   - **Project API keys** → `service_role` → Click "Reveal" → Copy

---

## Setting Up Your `.env`

```bash
# Copy the example
cp .env.example .env

# Edit .env and add your keys:
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # From "publishable" section
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."      # From "service_role" section (click Reveal)
```

---

## Testing Key Permissions

### Test Publishable Key (should respect RLS):
```python
from supabase import create_client

# Using publishable key
client = create_client(url, publishable_key)

# This should only return drivers where RLS policy allows
response = client.from_("drivers").select("*").execute()
print(f"Accessible drivers: {len(response.data)}")  # Limited by RLS
```

### Test Service Key (should bypass RLS):
```python
from supabase import create_client

# Using service key
admin = create_client(url, service_key)

# This returns ALL drivers (bypasses RLS)
response = admin.from_("drivers").select("*").execute()
print(f"Total drivers: {len(response.data)}")  # All drivers
```

---

## Summary

| Key | Use In | RLS | Expose? | Purpose |
|-----|--------|-----|---------|---------|
| **PUBLISHABLE_KEY** | Frontend | ✅ Enforced | ✅ Safe | User operations |
| **SERVICE_KEY** | Backend | ❌ Bypassed | 🔒 Never | Admin operations |

**Bottom line**: Keep both keys, use SERVICE_KEY in backend for admin operations, use PUBLISHABLE_KEY in frontend for user operations.
