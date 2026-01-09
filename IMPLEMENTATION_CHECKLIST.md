# Backend Implementation Checklist
**Find a Truck Driver - Backend Development**

Last Updated: 2026-01-08

---

## Phase 0: Project Setup & Infrastructure

### Git & Project Structure
- [ ] Initialize Git repository in `finddriverbackend/`
- [ ] Create `.gitignore` for Python/FastAPI
- [ ] Set up project folder structure
  - [ ] `app/` directory
  - [ ] `app/routers/` for API endpoints
  - [ ] `app/services/` for business logic
  - [ ] `app/models/` for data models
  - [ ] `app/utils/` for utilities
  - [ ] `tests/` directory
- [ ] Create `requirements.txt` with dependencies
- [ ] Create `README.md` for backend
- [ ] Set up virtual environment

### Configuration
- [ ] Create `.env.example` template
- [ ] Create `app/config.py` for environment variables
- [ ] Configure Supabase connection
- [ ] Configure Redis connection
- [ ] Set up logging configuration

---

## Phase 1: Core API Foundation (Week 1)

### FastAPI Setup
- [ ] Create `app/main.py` with FastAPI app
- [ ] Configure CORS for frontend
- [ ] Set up middleware (logging, error handling)
- [ ] Create health check endpoint (`GET /health`)
- [ ] Set up API versioning (`/api/v1/`)
- [ ] Configure async database connection pool

### Database Integration
- [ ] Set up Supabase client in `app/database.py`
- [ ] Create database connection dependencies
- [ ] Verify PostGIS extension is enabled
- [ ] Test database connectivity

### Data Models (Pydantic)
- [ ] `app/models/driver.py` - Driver model
- [ ] `app/models/location.py` - Location model
- [ ] `app/models/status.py` - Status enum and history
- [ ] `app/models/auth.py` - Auth request/response models
- [ ] `app/models/hotspot.py` - Hotspot model
- [ ] `app/models/facility.py` - Facility model

---

## Phase 2: Authentication System (Week 1-2)

### Phone OTP Authentication
- [ ] `app/routers/auth.py` - Auth endpoints
- [ ] `app/services/auth_service.py` - Auth business logic
- [ ] `POST /api/v1/auth/request-otp` - Send OTP
- [ ] `POST /api/v1/auth/verify-otp` - Verify OTP
- [ ] `POST /api/v1/auth/magic-link` - Email magic link (optional)
- [ ] `POST /api/v1/auth/refresh` - Refresh token
- [ ] JWT token generation and validation
- [ ] Phone number hashing utility
- [ ] Rate limiting for OTP requests
- [ ] Test OTP flow with Supabase test numbers

### Session Management
- [ ] `app/dependencies.py` - Auth dependencies
- [ ] `get_current_user()` dependency
- [ ] Token validation middleware
- [ ] Session expiry handling

---

## Phase 3: Onboarding System (Week 2)

### Handle Management
- [ ] `app/routers/onboarding.py` - Onboarding endpoints
- [ ] `app/services/handle_service.py` - Handle generation
- [ ] `app/utils/handle_generator.py` - Handle generation logic
- [ ] `POST /api/v1/onboarding/check-handle` - Check availability
- [ ] `GET /api/v1/onboarding/suggest-handles` - Generate suggestions
- [ ] Handle uniqueness validation
- [ ] Profanity filter for handles

### Avatar System
- [ ] `GET /api/v1/onboarding/avatars` - List available avatars
- [ ] Avatar ID validation

### Profile Creation
- [ ] `POST /api/v1/onboarding/complete` - Complete onboarding
- [ ] Create driver record in database
- [ ] Link driver to auth user
- [ ] Initial location capture

---

## Phase 4: Location Tracking (Week 2-3)

### Location Ingestion
- [ ] `app/routers/location.py` - Location endpoints
- [ ] `app/services/location_service.py` - Location business logic
- [ ] `app/utils/fuzz.py` - Location fuzzing utility
- [ ] `app/utils/geohash.py` - Geohash utility
- [ ] `POST /api/v1/location` - Update driver location
- [ ] Location validation (lat/lng bounds)
- [ ] Calculate geohash from coordinates
- [ ] Fuzz location for privacy (status-based radius)
- [ ] Store raw and fuzzed coordinates
- [ ] Update driver `last_active_at` timestamp

### Location Privacy
- [ ] Implement fuzzing algorithm
  - [ ] Rolling: 2-mile radius
  - [ ] Waiting: 1-mile radius
  - [ ] Parked: 0.5-mile radius
- [ ] Never expose raw coordinates via API
- [ ] Test fuzzing with sample coordinates

### Status Detection
- [ ] Auto-detect "rolling" from speed/heading
- [ ] Auto-detect "parked" from no movement
- [ ] Manual status override support

---

## Phase 5: Status Management (Week 3)

### Status Updates
- [ ] `app/routers/status.py` - Status endpoints
- [ ] `app/services/status_service.py` - Status business logic
- [ ] `PATCH /api/v1/status` - Update driver status
- [ ] Status validation (enum check)
- [ ] Create status_history record
- [ ] End previous status period
- [ ] Calculate duration for ended status

### Status History
- [ ] Track status transitions
- [ ] Calculate time spent in each status
- [ ] Query status history for analytics

---

## Phase 6: Real-Time System (Week 3-4)

### Redis Setup
- [ ] Configure Redis/Upstash connection
- [ ] `app/services/redis_service.py` - Redis operations
- [ ] Test Redis connectivity
- [ ] Set up connection pooling

### Stats Aggregation
- [ ] `app/services/stats_service.py` - Stats calculation
- [ ] Update global counters on location update
- [ ] Update regional counters (geohash-based)
- [ ] Update cluster stats
- [ ] Update facility stats
- [ ] Implement write-through cache pattern

### Real-Time Broadcasting
- [ ] `app/services/realtime_service.py` - Supabase Realtime
- [ ] Broadcast location updates to subscribers
- [ ] Channel naming strategy (by geohash)
- [ ] Subscribe to location channels
- [ ] Optimize payload size

---

## Phase 7: Map Data API (Week 4-5)

### Core Map Endpoint
- [ ] `app/routers/map.py` - Map data endpoints
- [ ] `app/services/map_service.py` - Map data logic
- [ ] `GET /api/v1/map/view` - Main map endpoint
- [ ] Bounding box validation
- [ ] Zoom level routing logic
- [ ] Current user injection (always included)
- [ ] Flag aggregates containing current user

### National View (z0-4)
- [ ] `app/services/map/national_view.py`
- [ ] Fetch regional aggregates from Redis
- [ ] Return regional bubbles
- [ ] Return highway corridor data
- [ ] Include current user floating marker

### State View (z5-8)
- [ ] `app/services/map/state_view.py`
- [ ] Fetch cluster data by geohash (precision 4)
- [ ] Select hero avatar for each cluster
- [ ] Override hero if current user in cluster
- [ ] Return cluster markers with counts

### Metro View (z9-12)
- [ ] `app/services/map/metro_view.py`
- [ ] Fetch facilities in bounding box
- [ ] Get avatar ring for each facility (6 visible)
- [ ] Prioritize current user to slot 1 (12 o'clock)
- [ ] Return facility markers with rings

### Local View (z13+)
- [ ] `app/services/map/local_view.py`
- [ ] Fetch detailed facility data
- [ ] Get full driver lists by status
- [ ] Fetch recent activity feed
- [ ] Return facility cards with details

### Hero & Ring Selection
- [ ] `app/utils/hero_selection.py`
- [ ] Implement hero selection algorithm
- [ ] Current user always becomes hero if present
- [ ] Most recent check-in for others
- [ ] Avatar ring selection (blend recency + engagement)
- [ ] Engagement score calculation

---

## Phase 8: Stats & Analytics (Week 5)

### Global Stats
- [ ] `app/routers/stats.py` - Stats endpoints
- [ ] `GET /api/v1/stats/global` - Global counters
- [ ] `GET /api/v1/stats/regional` - Regional stats by geohash
- [ ] Real-time counter updates

### Driver Queries
- [ ] `GET /api/v1/drivers/nearby` - Nearby drivers
- [ ] Radius-based spatial query
- [ ] Support for unauthenticated users (limited data)
- [ ] Return fuzzed locations only

---

## Phase 9: Hotspots & Facilities (Week 5-6)

### Hotspot Detection
- [ ] `app/services/hotspot_service.py` - Hotspot logic
- [ ] Auto-detect clusters of waiting drivers
- [ ] Minimum threshold for hotspot (e.g., 10+ waiting)
- [ ] Geofence matching to known facilities
- [ ] Create new hotspot if no facility match

### Facility Management
- [ ] `app/routers/facilities.py` - Facility endpoints
- [ ] `GET /api/v1/hotspots/nearby` - Nearby hotspots
- [ ] Calculate average wait times
- [ ] Update facility stats in real-time
- [ ] Reverse geocode hotspot names

### Wait Time Calculation
- [ ] Track wait start/end times
- [ ] Calculate rolling averages
- [ ] Store averages in facility_stats table
- [ ] Expose via API

---

## Phase 10: Background Jobs (Week 6)

### Scheduled Tasks
- [ ] Set up task scheduler (Celery or APScheduler)
- [ ] `app/jobs/refresh_cluster_stats.py` - Every 1 min
- [ ] `app/jobs/refresh_facility_rings.py` - Every 5 min
- [ ] `app/jobs/compute_detention_averages.py` - Every 15 min
- [ ] `app/jobs/detect_new_hotspots.py` - Every 1 hour
- [ ] `app/jobs/cleanup_inactive_drivers.py` - Every 5 min

### Cleanup Tasks
- [ ] Remove drivers inactive for 30+ minutes
- [ ] Update aggregate counts after removal
- [ ] Archive old status_history records
- [ ] Clean up expired OTP codes

---

## Phase 11: Testing (Week 6-7)

### Unit Tests
- [ ] Test location fuzzing algorithm
- [ ] Test geohash utilities
- [ ] Test handle generation
- [ ] Test hero selection logic
- [ ] Test engagement score calculation
- [ ] Test status transitions

### Integration Tests
- [ ] Test auth flow end-to-end
- [ ] Test onboarding flow
- [ ] Test location update -> stats update
- [ ] Test map data endpoints
- [ ] Test real-time broadcasting

### Load Tests
- [ ] Simulate 1,000 concurrent drivers
- [ ] Simulate 10,000 location updates/min
- [ ] Test Redis performance under load
- [ ] Test database query performance
- [ ] Optimize slow queries

---

## Phase 12: Security & Performance (Week 7)

### Security
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] Rate limiting on auth endpoints
- [ ] Rate limiting on location updates
- [ ] CORS configuration
- [ ] Helmet middleware for headers
- [ ] Prevent phone number enumeration
- [ ] Token expiry enforcement

### Performance Optimization
- [ ] Database indexes on critical columns
- [ ] Redis caching strategy
- [ ] Connection pooling
- [ ] Async/await optimization
- [ ] Query optimization (EXPLAIN ANALYZE)
- [ ] Payload size optimization
- [ ] Compression middleware

---

## Phase 13: Deployment Preparation (Week 7-8)

### Infrastructure
- [ ] Create `Dockerfile` for FastAPI app
- [ ] Create `docker-compose.yml` for local dev
- [ ] Set up Railway/Fly.io deployment
- [ ] Configure environment variables in deployment
- [ ] Set up Redis in production (Upstash)
- [ ] Verify Supabase production connection

### Monitoring & Logging
- [ ] Set up application logging
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring (New Relic/DataDog)
- [ ] Database query logging
- [ ] API endpoint metrics

### Documentation
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Deployment guide
- [ ] Environment setup guide
- [ ] Database migration guide

---

## Phase 14: Launch Preparation (Week 8)

### Pre-Launch Checklist
- [ ] End-to-end testing with frontend
- [ ] Load testing with realistic data
- [ ] Backup strategy implemented
- [ ] Rollback plan documented
- [ ] Error alerting configured
- [ ] Performance baselines established

### Beta Launch
- [ ] Deploy to staging environment
- [ ] Test with small group of beta users
- [ ] Monitor for errors
- [ ] Gather feedback
- [ ] Fix critical issues

### Production Launch
- [ ] Deploy to production
- [ ] Monitor metrics closely
- [ ] Be ready for hotfixes
- [ ] Celebrate! 🎉

---

## Ongoing Maintenance

### Weekly
- [ ] Review error logs
- [ ] Check performance metrics
- [ ] Monitor database growth
- [ ] Review Redis memory usage

### Monthly
- [ ] Database optimization
- [ ] Clean up old data
- [ ] Review security patches
- [ ] Update dependencies

---

## Notes
- Each checkbox represents a concrete deliverable
- Estimated timeline: 8 weeks for MVP
- Priorities: P0 (must have), P1 (should have), P2 (nice to have)
- This is a living document - update as we progress
