# Supabase API Keys Guide

## TL;DR

✅ **Use NEW keys** (preferred): `SUPABASE_PUBLISHABLE_KEY` + `SUPABASE_SECRET_KEY`
⚠️ **Legacy keys still work**: `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY`

Our backend supports **BOTH** key types with automatic fallback.

---

## The New Supabase Key System (2024+)

Supabase is transitioning from JWT-based keys to non-JWT keys for better security and performance.

### 1. SUPABASE_PUBLISHABLE_KEY (NEW)

**Format**: `sb_publishable_...`

**Where to find**: Supabase Dashboard → Project Settings → API → "Publishable key"

**Characteristics**:
- ✅ **Safe to expose** in frontend code, mobile apps, CLIs
- ✅ **RLS enforced** - respects Row Level Security policies
- ✅ Low privileges - users access only allowed data
- 🆕 Non-JWT based (faster, more secure)

**Use for**:
- Frontend authentication
- Mobile app API calls
- User-specific queries
- Any client-side operations

**Example** (Frontend):
```typescript
// ✅ Safe to expose in frontend
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!  // Safe in browser
)
```

---

### 2. SUPABASE_SECRET_KEY (NEW)

**Format**: `sb_secret_...`

**Where to find**: Supabase Dashboard → Project Settings → API → "Secret key" (click Reveal)

**Characteristics**:
- 🔒 **NEVER expose** - backend/server-side only
- 🔒 **Bypasses RLS** - full database access
- 🔒 Elevated privileges - admin operations
- 🆕 Non-JWT based

**Use for**:
- Backend API operations
- Admin tasks
- System operations (stats, cleanup)
- Operations across all users

**Example** (Backend):
```python
# 🔒 Backend only - never expose
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]  # Admin access
)
```

---

## Legacy Keys (Still Supported)

### 3. SUPABASE_ANON_KEY (LEGACY)

**Format**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Equivalent to**: `SUPABASE_PUBLISHABLE_KEY`

- JWT-based (older format)
- Same functionality as publishable key
- Still works, but new projects should use publishable key

---

### 4. SUPABASE_SERVICE_ROLE_KEY (LEGACY)

**Format**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Equivalent to**: `SUPABASE_SECRET_KEY`

- JWT-based (older format)
- Same functionality as secret key
- Still works, but new projects should use secret key

---

## Our Backend Configuration

Our `config.py` supports **BOTH** key types with smart fallback:

```python
# Tries new keys first, falls back to legacy keys
@property
def supabase_client_key(self) -> str:
    """Returns: publishable_key OR anon_key"""
    return self.supabase_publishable_key or self.supabase_anon_key

@property
def supabase_admin_key(self) -> str:
    """Returns: secret_key OR service_role_key"""
    return self.supabase_secret_key or self.supabase_service_role_key
```

**This means you can use**:
- ✅ New keys only
- ✅ Legacy keys only
- ✅ Mix of both (will prefer new keys)

---

## Setting Up Your Keys

### Option 1: Using NEW Keys (Recommended)

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Project Settings → API
3. Copy **"Publishable key"** → `SUPABASE_PUBLISHABLE_KEY`
4. Click **Reveal** on "Secret key" → Copy → `SUPABASE_SECRET_KEY`

```bash
# .env
SUPABASE_URL="https://yourproject.supabase.co"
SUPABASE_PUBLISHABLE_KEY="sb_publishable_..."  # ✅ New format
SUPABASE_SECRET_KEY="sb_secret_..."            # ✅ New format
```

### Option 2: Using Legacy Keys (Still Works)

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Project Settings → API
3. Copy **"anon / public"** → `SUPABASE_ANON_KEY`
4. Copy **"service_role"** → `SUPABASE_SERVICE_ROLE_KEY`

```bash
# .env
SUPABASE_URL="https://yourproject.supabase.co"
SUPABASE_ANON_KEY="eyJhbGc..."                    # Legacy JWT
SUPABASE_SERVICE_ROLE_KEY="eyJhbGc..."            # Legacy JWT
```

### Option 3: Both (Maximum Compatibility)

```bash
# .env - Both sets of keys
SUPABASE_URL="https://yourproject.supabase.co"

# New keys (preferred)
SUPABASE_PUBLISHABLE_KEY="sb_publishable_..."
SUPABASE_SECRET_KEY="sb_secret_..."

# Legacy keys (fallback)
SUPABASE_ANON_KEY="eyJhbGc..."
SUPABASE_SERVICE_ROLE_KEY="eyJhbGc..."
```

---

## Why We Need Admin/Secret Keys in Backend

Our FastAPI backend **requires the admin key** (secret or service_role) because:

### 1. Stats Aggregation
```python
# Count ALL drivers across regions (needs admin access)
all_drivers = supabase.from_("drivers") \
    .select("*") \
    .gte("last_active", thirty_mins_ago) \
    .execute()  # Returns all drivers (bypasses RLS)
```

### 2. Map Data Generation
```python
# Get aggregated data for map view (all users)
clusters = supabase.from_("cluster_stats") \
    .select("*") \
    .in_("geohash", geohashes) \
    .execute()  # Admin access needed
```

### 3. Hotspot Detection
```python
# Analyze waiting drivers system-wide
waiting_drivers = supabase.from_("drivers") \
    .select("*, driver_locations(*)") \
    .eq("status", "waiting") \
    .execute()  # Needs to see all waiting drivers
```

### 4. System Operations
- Cleanup old data
- Calculate averages
- Update facility stats
- Background jobs

**Without admin key**: These operations would fail due to RLS restrictions.

---

## Key Comparison Table

| Feature | Publishable / Anon | Secret / Service Role |
|---------|-------------------|----------------------|
| **Format** | `sb_publishable_...` or JWT | `sb_secret_...` or JWT |
| **RLS** | ✅ Enforced | ❌ Bypassed |
| **Frontend Safe** | ✅ Yes | 🔒 Never |
| **Use In** | Client-side | Server-side only |
| **Access Level** | User data only | All data (admin) |
| **Required For** | Auth, user queries | Stats, admin ops |

---

## Security Best Practices

### ✅ DO:
- Use **new keys** (`sb_publishable_...` / `sb_secret_...`) for new projects
- Store secret/service_role keys in `.env` only
- Use secret key only in backend code
- Use publishable/anon key in frontend
- Add `.env` to `.gitignore`
- Rotate keys if compromised

### ❌ DON'T:
- Expose secret/service_role key in frontend
- Commit secret keys to Git
- Use admin keys in client JavaScript
- Share secret keys publicly
- Hardcode keys in source code

---

## Testing Your Keys

### Test Client Key (should respect RLS):
```python
from supabase import create_client
from app.config import settings

# Using client key (publishable or anon)
client = create_client(
    settings.supabase_url,
    settings.supabase_client_key  # Our helper property
)

# Should only return data allowed by RLS
response = client.from_("drivers").select("*").execute()
print(f"Accessible: {len(response.data)}")  # Limited by RLS
```

### Test Admin Key (should bypass RLS):
```python
from supabase import create_client
from app.config import settings

# Using admin key (secret or service_role)
admin = create_client(
    settings.supabase_url,
    settings.supabase_admin_key  # Our helper property
)

# Should return ALL data (bypasses RLS)
response = admin.from_("drivers").select("*").execute()
print(f"Total: {len(response.data)}")  # All drivers
```

---

## Migration Guide

### If you have legacy keys:
✅ **Keep them** - they still work fine
✅ **Add new keys** when available - our code supports both
✅ **No code changes needed** - automatic fallback

### Getting new keys:
1. Supabase Dashboard → Project Settings → API
2. Look for "Publishable key" and "Secret key" sections
3. If you see `sb_publishable_...` format, you have new keys
4. If you only see JWT keys, legacy keys are still active

---

## Summary

| Key Type | Format | Use | Expose? | RLS |
|----------|--------|-----|---------|-----|
| **NEW: Publishable** | `sb_publishable_...` | Frontend | ✅ Safe | ✅ Enforced |
| **NEW: Secret** | `sb_secret_...` | Backend | 🔒 Never | ❌ Bypassed |
| **Legacy: Anon** | JWT `eyJh...` | Frontend | ✅ Safe | ✅ Enforced |
| **Legacy: Service Role** | JWT `eyJh...` | Backend | 🔒 Never | ❌ Bypassed |

**Our backend works with both** - use whichever keys your Supabase project provides!
