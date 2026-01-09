# Find a Truck Driver - Backend API

FastAPI backend for the Find a Truck Driver real-time truck driver tracking platform.

## 🚛 Overview

This backend powers a real-time, anonymous truck driver tracking application that displays driver locations and statuses across the United States. The system is designed to handle 50,000+ concurrent drivers with real-time location updates.

## 🏗️ Architecture

- **Framework**: FastAPI (Python 3.11+)
- **Database**: Supabase (PostgreSQL + PostGIS)
- **Cache**: Redis/Upstash
- **Real-Time**: Supabase Realtime + WebSockets
- **Authentication**: Supabase Auth (Phone OTP)

## 📋 Features

- **Phone OTP Authentication**: Passwordless login via SMS
- **Real-Time Location Tracking**: GPS tracking with privacy-first fuzzing
- **Status Management**: Rolling, Waiting, Parked status tracking
- **Map Data API**: Four-tier zoom-based visualization system
- **Hotspot Detection**: Automatic detection of detention areas
- **Stats Aggregation**: Real-time global and regional statistics
- **WebSocket Broadcasting**: Live updates to connected clients

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with PostGIS (via Supabase)
- Redis server
- Supabase account

### Installation

1. **Clone the repository** (if not already done)

2. **Navigate to backend directory**
   ```bash
   cd finddriverbackend
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

6. **Run database migrations** (when available)
   ```bash
   # TODO: Add migration commands
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc

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

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/request-otp` - Request OTP code
- `POST /api/v1/auth/verify-otp` - Verify OTP and login
- `POST /api/v1/auth/refresh` - Refresh access token

### Onboarding
- `POST /api/v1/onboarding/check-handle` - Check handle availability
- `GET /api/v1/onboarding/suggest-handles` - Get handle suggestions
- `GET /api/v1/onboarding/avatars` - List available avatars
- `POST /api/v1/onboarding/complete` - Complete onboarding

### Location & Status
- `POST /api/v1/location` - Update driver location
- `PATCH /api/v1/status` - Update driver status
- `GET /api/v1/drivers/nearby` - Get nearby drivers

### Map Data
- `GET /api/v1/map/view` - Get map data (zoom-aware)

### Statistics
- `GET /api/v1/stats/global` - Global driver counts
- `GET /api/v1/stats/regional` - Regional statistics

### Hotspots & Facilities
- `GET /api/v1/hotspots/nearby` - Get nearby hotspots
- `GET /api/v1/facilities/{id}` - Get facility details

## 🔐 Authentication

The API uses JWT tokens for authentication:

1. Request OTP via phone number
2. Verify OTP to receive access token
3. Include token in `Authorization: Bearer <token>` header
4. Refresh token before expiry

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

- [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md) - Development roadmap
- [Audit Log](AUDIT_LOG.md) - Decision tracking
- [Error Tracker](ERROR_TRACKER.md) - Known issues

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
