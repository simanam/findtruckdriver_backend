# Find a Truck Driver - Backend API

FastAPI backend for the Find a Truck Driver real-time truck driver tracking platform.

## 🚛 Overview

This backend powers a real-time, anonymous truck driver tracking application that displays driver locations and statuses across the United States.

## 🏗️ Architecture

- **Framework**: FastAPI (Python 3.9+)
- **Database**: Supabase (PostgreSQL + PostGIS)
- **Cache**: Redis (configured, not yet integrated)
- **Authentication**: Supabase Auth (Email OTP, Phone OTP, Magic Link)

## 📋 Features

- **Email OTP Authentication**: Passwordless login via email (FREE with Supabase)
- **Phone OTP**: Alternative SMS authentication
- **Magic Link**: Email-based authentication
- **Location Tracking**: Privacy-first location fuzzing
- **Status Management**: Rolling, Waiting, Parked status tracking
- **Map Search**: Find nearby drivers, clusters, hotspots
- **Statistics**: Real-time activity metrics
- **22 API Endpoints**: Complete REST API

## 🎯 Quick Start for Frontend Developers

**→ [FRONTEND_SETUP.md](./FRONTEND_SETUP.md)** - Get your frontend connected in 5 minutes!

**Complete Documentation:**
- [Quick Start Guide](./docs/QUICK_START_FRONTEND.md) - All endpoints with examples
- [API URLs Reference](./docs/API_URLS_REFERENCE.md) - Copy & paste ready URLs
- [Troubleshooting](./docs/FRONTEND_TROUBLESHOOTING.md) - Common issues & solutions
- [Full Integration Guide](./docs/FRONTEND_INTEGRATION.md) - Complete React Native code

## 🚀 Quick Start for Backend

### Prerequisites

- Python 3.9+
- Supabase account (database included)
- Your Supabase API keys

### Installation

1. **Navigate to backend directory**
   ```bash
   cd finddriverbackend
   ```

2. **Run setup script**
   ```bash
   ./setup.sh
   ```
   This creates venv and installs all dependencies.

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

   Required variables:
   ```bash
   SUPABASE_URL="https://your-project.supabase.co"
   SUPABASE_PUBLISHABLE_KEY="sb_publishable_..."
   SUPABASE_SECRET_KEY="sb_secret_..."
   DATABASE_URL="postgresql://..."
   ```

4. **Start the development server**
   ```bash
   ./run_dev.sh
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Test It Works

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}
```

## 📁 Project Structure

```
finddriverbackend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── dependencies.py         # Shared dependencies
│   ├── database.py             # Database connection
│   ├── routers/                # API route handlers
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── onboarding.py      # Onboarding flow
│   │   ├── location.py        # Location updates
│   │   ├── status.py          # Status management
│   │   ├── map.py             # Map data endpoints
│   │   ├── stats.py           # Statistics
│   │   └── facilities.py      # Facility/hotspot data
│   ├── services/              # Business logic
│   │   ├── auth_service.py
│   │   ├── location_service.py
│   │   ├── status_service.py
│   │   ├── map_service.py
│   │   ├── stats_service.py
│   │   ├── hotspot_service.py
│   │   ├── redis_service.py
│   │   └── realtime_service.py
│   ├── models/                # Pydantic models
│   │   ├── driver.py
│   │   ├── location.py
│   │   ├── status.py
│   │   ├── auth.py
│   │   ├── facility.py
│   │   └── hotspot.py
│   └── utils/                 # Utility functions
│       ├── fuzz.py           # Location fuzzing
│       ├── geohash.py        # Geohash utilities
│       ├── handle_generator.py
│       └── hero_selection.py
├── tests/                     # Test suite
├── logs/                      # Application logs
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── .gitignore
├── README.md                # This file
├── IMPLEMENTATION_CHECKLIST.md
├── AUDIT_LOG.md
└── ERROR_TRACKER.md
```

## 🔌 API Endpoints (22 Total)

### Authentication (8 endpoints)
- `POST /api/v1/auth/email/otp/request` - Request email OTP (FREE)
- `POST /api/v1/auth/email/otp/verify` - Verify email OTP
- `POST /api/v1/auth/otp/request` - Request phone OTP
- `POST /api/v1/auth/otp/verify` - Verify phone OTP
- `POST /api/v1/auth/magic-link/request` - Request magic link
- `POST /api/v1/auth/token/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout user
- `GET /api/v1/auth/me` - Get current user

### Driver Profile (6 endpoints)
- `POST /api/v1/drivers` - Create driver profile
- `GET /api/v1/drivers/me` - Get my profile
- `PATCH /api/v1/drivers/me` - Update my profile
- `PATCH /api/v1/drivers/me/status` - Update status only
- `GET /api/v1/drivers/{handle}` - Get driver by handle
- `GET /api/v1/drivers/id/{driver_id}` - Get driver by ID

### Location & Check-in (4 endpoints)
- `POST /api/v1/locations/check-in` - Manual check-in
- `POST /api/v1/locations/status/update` - Update status with location
- `GET /api/v1/locations/me` - Get my current location
- `GET /api/v1/locations/nearby` - Find nearby drivers

### Map & Search (4 endpoints)
- `GET /api/v1/map/drivers` - Get drivers in map area
- `GET /api/v1/map/clusters` - Get driver clusters
- `GET /api/v1/map/hotspots` - Get hotspot locations
- `GET /api/v1/map/stats` - Get map statistics

**See [docs/API_URLS_REFERENCE.md](./docs/API_URLS_REFERENCE.md) for complete endpoint list with examples.**

## 🔐 Authentication

**Recommended: Email OTP (Free, No SMS Costs)**

1. User enters email → `POST /api/v1/auth/email/otp/request`
2. User receives 8-digit code in email
3. User enters code → `POST /api/v1/auth/email/otp/verify`
4. Receive access_token and refresh_token
5. Include token in all requests: `Authorization: Bearer <token>`

**See [FRONTEND_SETUP.md](./FRONTEND_SETUP.md) for complete authentication guide.**

## 🗺️ Location Privacy

All driver locations are **fuzzed** for privacy:

- **Rolling**: ±2 miles
- **Waiting**: ±1 mile
- **Parked**: ±0.5 miles

Raw coordinates are **never** exposed via API. Only fuzzed coordinates are returned.

## 📊 Real-Time Updates

The system uses Supabase Realtime for broadcasting location updates:

**Channels**:
- `locations:global` - All updates (national view)
- `locations:{geohash}` - Regional updates (4-char geohash)
- `stats:global` - Real-time counter updates
- `hotspots:{id}` - Facility-specific updates

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_location_service.py

# Run with verbose output
pytest -v
```

## 🚢 Deployment

### Using Docker (TODO)

```bash
docker build -t finddriverapi .
docker run -p 8000:8000 --env-file .env finddriverapi
```

### Using Railway/Fly.io (TODO)

See deployment guide in documentation.

## 📈 Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (when implemented)
- **Logs**: Check `logs/app.log`

## 🛠️ Development

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/

# Type check
mypy app/
```

### Database Migrations

```bash
# TODO: Add Alembic migration commands when implemented
```

## 📝 Documentation

### For Frontend Developers
- **[FRONTEND_SETUP.md](./FRONTEND_SETUP.md)** - 5-minute setup guide ⭐
- **[docs/QUICK_START_FRONTEND.md](./docs/QUICK_START_FRONTEND.md)** - All endpoints with examples
- **[docs/API_URLS_REFERENCE.md](./docs/API_URLS_REFERENCE.md)** - Complete URL list
- **[docs/FRONTEND_TROUBLESHOOTING.md](./docs/FRONTEND_TROUBLESHOOTING.md)** - Common issues
- **[docs/FRONTEND_INTEGRATION.md](./docs/FRONTEND_INTEGRATION.md)** - Full integration guide

### For Backend Developers
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Backend overview
- **[API_ENDPOINTS.md](./API_ENDPOINTS.md)** - API reference
- **[docs/EMAIL_OTP_SETUP.md](./docs/EMAIL_OTP_SETUP.md)** - Email authentication guide
- **[docs/SUPABASE_EMAIL_CONFIG.md](./docs/SUPABASE_EMAIL_CONFIG.md)** - Supabase config
- **[docs/database_schema.sql](./docs/database_schema.sql)** - Database schema

## 🤝 Contributing

1. Follow the implementation checklist
2. Write tests for new features
3. Update documentation
4. Log decisions in AUDIT_LOG.md
5. Document errors in ERROR_TRACKER.md

## 📄 License

[Add license information]

## 🆘 Support

For issues and questions, check ERROR_TRACKER.md or create an issue.

---

**Status**: 🚧 In Active Development

**Last Updated**: 2026-01-08
