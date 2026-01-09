# Backend Setup and Run Guide

## Prerequisites

- Python 3.11+ installed
- Supabase account with project set up
- Redis (optional for now - can skip for basic testing)

---

## Step 1: Create Virtual Environment

```bash
# Navigate to backend directory
cd /Users/amansingh/Documents/findtruckdriver/finddriverapp/finddriverbackend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
# venv\Scripts\activate  # On Windows
```

**Verify activation**: Your terminal prompt should now show `(venv)` prefix.

---

## Step 2: Install Dependencies

```bash
# Make sure venv is activated (you should see (venv) in prompt)
pip install --upgrade pip

# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

This will install:

- FastAPI, uvicorn
- Supabase client
- Redis client
- Geospatial libraries
- Testing tools
- And more...

**Expected time**: 2-3 minutes depending on internet speed.

---

## Step 3: Verify .env File

Make sure your `.env` file exists and has the required values:

```bash
# Check if .env exists
ls -la .env

# View .env (to verify it has values)
cat .env
```

**Required variables**:

```bash
SUPABASE_URL="https://yourproject.supabase.co"
SUPABASE_SECRET_KEY="sb_secret_..."  # OR SUPABASE_SERVICE_ROLE_KEY="eyJh..."
DATABASE_URL="postgresql://postgres:yourpass@db.yourproject.supabase.co:5432/postgres"
JWT_SECRET_KEY="your-secret-key"
```

**Optional for basic testing** (can be defaults):

- `REDIS_URL` (defaults to `redis://localhost:6379`)
- Other feature flags

---

## Step 4: Run the Server

### Option A: Development Mode (with auto-reload)

```bash
# Make sure venv is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Flags explained**:

- `--reload`: Auto-restart when code changes
- `--host 0.0.0.0`: Allow external connections
- `--port 8000`: Run on port 8000

### Option B: Using Python directly

```bash
python app/main.py
```

This will use settings from `config.py` (host, port, etc.)

### Option C: Production-like (no reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Step 5: Verify Server is Running

You should see output like:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
🚀 Starting Find a Truck Driver API
INFO:     Environment: development
INFO:     Debug Mode: True
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Step 6: Test the API

### In Browser:

1. **API Documentation**: http://localhost:8000/docs

   - Interactive Swagger UI
   - Try out endpoints directly

2. **Alternative Docs**: http://localhost:8000/redoc

   - Clean, readable documentation

3. **Health Check**: http://localhost:8000/health

   - Should return: `{"status": "healthy", "version": "1.0.0", ...}`

4. **Root**: http://localhost:8000/
   - API information and links

### In Terminal:

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# Pretty print with jq (if installed)
curl http://localhost:8000/health | jq
```

---

## Common Issues & Solutions

### Issue 1: `ModuleNotFoundError`

**Problem**: Missing dependencies

**Solution**:

```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 2: `ValidationError` on startup

**Problem**: Missing or invalid environment variables

**Solution**:

```bash
# Check .env file exists
cat .env

# Verify required variables are set
# Fix any missing values
```

### Issue 3: Port already in use

**Problem**: Another process using port 8000

**Solution**:

```bash
# Use a different port
uvicorn app.main:app --reload --port 8001

# OR kill the process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Issue 4: Can't connect to Supabase

**Problem**: Invalid Supabase credentials

**Solution**:

- Double-check `SUPABASE_URL` in .env
- Verify `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY`
- Check Supabase Dashboard → Project Settings → API

### Issue 5: Redis connection error

**Problem**: Redis not running (but it's optional for basic testing)

**Solution**:

```bash
# Option 1: Install and start Redis locally
brew install redis  # macOS
redis-server

# Option 2: Skip Redis features for now
# They'll be implemented later
```

---

## Development Workflow

### 1. Start development session:

```bash
cd /Users/amansingh/Documents/findtruckdriver/finddriverapp/finddriverbackend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 2. Make changes to code

- Server auto-reloads on file save

### 3. Test changes:

- Visit http://localhost:8000/docs
- Use curl or Postman
- Check logs in terminal

### 4. When done:

```bash
# Stop server: CTRL+C

# Deactivate venv
deactivate
```

---

## Quick Commands Reference

```bash
# Activate venv
source venv/bin/activate

# Run server (dev mode)
uvicorn app.main:app --reload

# Run tests (when we add them)
pytest

# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/

# View logs
tail -f logs/app.log

# Deactivate venv
deactivate
```

---

## Next Steps After Server Runs

Once your server is running successfully:

1. ✅ Test health endpoint works
2. ✅ Verify Swagger docs load at `/docs`
3. 📝 Begin implementing Phase 1: Database integration
4. 📝 Create Pydantic models
5. 📝 Set up Supabase client
6. 📝 Implement authentication endpoints

---

## Environment Variables Quick Reference

### Required:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`)
- `DATABASE_URL`
- `JWT_SECRET_KEY`

### Optional (have defaults):

- `HOST` (default: 0.0.0.0)
- `PORT` (default: 8000)
- `DEBUG` (default: True)
- `REDIS_URL` (default: redis://localhost:6379)
- All feature flags (defaults in config.py)

---

## Troubleshooting Checklist

- [ ] Virtual environment activated? (`(venv)` in prompt)
- [ ] Dependencies installed? (`pip list` shows packages)
- [ ] `.env` file exists in backend root?
- [ ] Required env vars set in `.env`?
- [ ] Port 8000 available? (not used by another app)
- [ ] Python 3.11+ installed? (`python --version`)
- [ ] In correct directory? (`pwd` shows finddriverbackend)

---

**Need help?** Check [ERROR_TRACKER.md](ERROR_TRACKER.md) or [AUDIT_LOG.md](AUDIT_LOG.md)

wo Separate Tables:

1. drivers table (Profile Info - NO location)

CREATE TABLE drivers (
id UUID PRIMARY KEY,
user_id UUID,
handle VARCHAR(30),
avatar_id TEXT,
status VARCHAR(20), -- Just status, no location
last_active TIMESTAMPTZ,
created_at TIMESTAMPTZ
); 2. driver_locations table (Location Tracking - Separate)

CREATE TABLE driver_locations (
id UUID PRIMARY KEY,
driver_id UUID,
location GEOGRAPHY(POINT), -- Raw GPS
fuzzed_location GEOGRAPHY(POINT), -- Privacy-fuzzed
accuracy FLOAT,
heading FLOAT,
speed FLOAT,
geohash VARCHAR(12),
recorded_at TIMESTAMPTZ
);
So the flow is:
During Onboarding:

✅ Create driver profile (handle, avatar, status)
❌ NO location collected yet
After Onboarding (on Map Screen):

User's location is tracked via background services
Location updates sent to POST /api/v1/locations/check-in
Stored in driver_locations table (separate from profile)
This is good design because:

User can create profile without granting location permission
Location is optional until they actually use the map
Privacy - location and profile are decoupled
Is this the behavior you want, or do you want to collect location during onboarding?

because with status update we should be collecting current lcoation to show on map right
Yes, absolutely! You're right - when a user updates their status (rolling/waiting/parked), you should also collect their current location so they appear on the map.

Let me check the status update endpoint to see if it already handles location:

Read locations.py
Perfect! The backend already supports this. You have two endpoints for location tracking:

1. POST /api/v1/locations/status/update (Lines 127-263)
   Use this when changing status - Updates BOTH status AND location in one call

Request:

{
"status": "rolling", // New status
"latitude": 40.7128,
"longitude": -74.0060,
"accuracy": 10.0, // Optional
"heading": 180.0, // Optional
"speed": 65.0 // Optional
}
What it does:

Updates driver status (rolling/waiting/parked)
Saves location with privacy fuzzing
Closes old status history
Creates new status history entry
Returns fuzzed location for display on map 2. POST /api/v1/locations/check-in (Lines 30-117)
Use this to refresh location without changing status

Request:

{
"latitude": 40.7128,
"longitude": -74.0060,
"accuracy": 10.0,
"heading": 180.0,
"speed": 65.0
}
Your Current Onboarding Flow Should Be:
Step 1-3: Collect handle, avatar, status (NO location yet)
Step 4: Email OTP verification
After verification: Create profile with handle/avatar/status
Redirect to /map: Request location permission
Once permission granted: Call /locations/status/update with their selected status + current location
So your frontend should:

// After onboarding, when user lands on map screen
async function initializeUserOnMap() {
// Request location permission
const location = await getCurrentLocation();

    // Send status + location to appear on map
    await api.locations.updateStatus({
        status: useOnboardingStore.getState().status, // From onboarding
        latitude: location.latitude,
        longitude: location.longitude,
        accuracy: location.accuracy,
        heading: location.heading,
        speed: location.speed
    });

    // Now user appears on map!

}
Does your frontend currently call /locations/status/update or /locations/check-in after onboarding completes?
