# Deployment & Security Guide

Complete guide for deploying FindTruckDriver backend securely on Railway.

---

## Security Features Implemented

### 1. Authentication
- JWT tokens via Supabase Auth
- All protected endpoints require valid Bearer token
- Token validation on every request

### 2. Rate Limiting
Rate limits implemented using SlowAPI:

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| OTP Request (phone) | 5/hour | Prevent SMS bombing |
| OTP Request (email) | 5/hour | Prevent email bombing |
| OTP Verify | 10/minute | Prevent brute force |
| Magic Link | 5/hour | Prevent email bombing |
| General API | 100/minute | Global protection |

### 3. Security Headers
All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### 4. Production Mode
When `ENVIRONMENT=production`:
- `/docs` disabled (no Swagger UI)
- `/redoc` disabled
- `/openapi.json` disabled
- Validation errors don't expose details
- Internal errors don't expose stack traces

### 5. CORS
Configured via `CORS_ORIGINS` environment variable:
- Development: `http://localhost:3000`
- Production: Your actual frontend URL only

### 6. Input Validation
- All inputs validated via Pydantic models
- SQL injection protected (Supabase parameterized queries)
- Location coordinates validated (lat: -90 to 90, lng: -180 to 180)

---

## Railway Deployment

### Step 1: Environment Variables

Set these in Railway dashboard:

```env
# Required
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your_publishable_key
SUPABASE_SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://...

# CORS (Required - your frontend URL)
CORS_ORIGINS=https://your-app.vercel.app,https://yourdomain.com

# Optional
SENTRY_DSN=https://xxx@sentry.io/xxx
REDIS_URL=redis://...
```

### Step 2: Railway Configuration

Create `railway.json` in project root:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```

### Step 3: Procfile (Alternative)

Create `Procfile`:

```
web: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### Step 4: Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Must be "production" | `production` |
| `DEBUG` | Must be "false" | `false` |
| `SUPABASE_URL` | Your Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Public API key | `eyJ...` |
| `SUPABASE_SECRET_KEY` | Service role key | `eyJ...` |
| `DATABASE_URL` | Postgres connection string | `postgresql://...` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `https://app.com` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `REDIS_URL` | localhost | Redis for caching |
| `SENTRY_DSN` | - | Error monitoring |
| `PORT` | 8000 | Server port (Railway sets this) |

---

## Security Checklist

Before deploying to production:

### Environment
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] All secrets in environment variables (not code)
- [ ] No `.env` file in git

### CORS
- [ ] Only your frontend domain in `CORS_ORIGINS`
- [ ] No `*` wildcards
- [ ] No localhost URLs in production

### Supabase
- [ ] RLS enabled on all tables
- [ ] Service key only used server-side
- [ ] Publishable key for client operations

### Monitoring
- [ ] Sentry configured for error tracking
- [ ] Health check endpoint working
- [ ] Logging configured

### Database
- [ ] Connection pooling enabled
- [ ] SSL required for connections
- [ ] Backups configured

---

## Public vs Protected Endpoints

### Public Endpoints (No Auth)

These endpoints are intentionally public:

| Endpoint | Purpose | Protection |
|----------|---------|------------|
| `/health` | Health checks | None needed |
| `/api/v1/auth/*` | Authentication | Rate limited |
| `/api/v1/map/drivers` | View map | Read-only, no PII |
| `/api/v1/map/weather` | Weather data | Rate limited |
| `/api/v1/map/stats/global` | Global stats | Aggregated only |
| `/api/v1/drivers/{id}` | Public profile | Limited fields |

These are safe because:
- Read-only access
- No sensitive data exposed
- Rate limited
- Location data is fuzzed

### Protected Endpoints (Auth Required)

| Endpoint | Requires |
|----------|----------|
| `/api/v1/drivers/me` | Auth token |
| `/api/v1/drivers/me/status` | Auth token |
| `/api/v1/drivers/me/stats` | Auth token |
| `/api/v1/locations/*` | Auth token |
| `/api/v1/follow-ups/*` | Auth token |

---

## Monitoring & Alerts

### Health Check

Railway uses `/health` endpoint:

```bash
curl https://your-api.railway.app/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### Error Tracking (Sentry)

Set `SENTRY_DSN` to enable:
- Automatic error capture
- Performance monitoring
- Release tracking

### Logs

Access via Railway dashboard or CLI:
```bash
railway logs
```

---

## Rate Limit Responses

When rate limited, users receive:

```json
{
  "error": "Rate limit exceeded: 5 per 1 hour"
}
```

HTTP Status: `429 Too Many Requests`

Headers:
- `Retry-After`: Seconds until limit resets
- `X-RateLimit-Limit`: Max requests
- `X-RateLimit-Remaining`: Requests left
- `X-RateLimit-Reset`: Reset timestamp

---

## Security Incident Response

### If API Keys Leaked

1. **Immediately rotate keys in Supabase**
2. Update Railway environment variables
3. Redeploy application
4. Check logs for unauthorized access
5. Review git history for exposed secrets

### If Suspicious Traffic Detected

1. Check rate limit logs
2. Block IP addresses if needed (Railway firewall)
3. Review affected endpoints
4. Enable additional monitoring

### If Data Breach Suspected

1. Disable affected endpoints
2. Audit database access logs
3. Notify affected users (if PII exposed)
4. Document incident timeline

---

## Testing Production Readiness

### Local Production Test

```bash
# Set production environment
export ENVIRONMENT=production
export DEBUG=false
export CORS_ORIGINS=https://your-app.com

# Run with production settings
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Should return 404

# Test rate limiting
for i in {1..10}; do curl -X POST http://localhost:8000/api/v1/auth/otp/request -d '{"phone":"+1234567890"}'; done
```

### Production Verification

After deployment:

```bash
# Health check
curl https://your-api.railway.app/health

# Docs disabled
curl https://your-api.railway.app/docs  # Should 404

# CORS working
curl -H "Origin: https://not-allowed.com" https://your-api.railway.app/api/v1/map/drivers
# Should fail CORS

# Rate limiting active
# Make 6 OTP requests - 6th should return 429
```

---

## Summary

### Security Measures Active

| Feature | Status |
|---------|--------|
| JWT Authentication | ✅ |
| Rate Limiting | ✅ |
| Security Headers | ✅ |
| CORS Protection | ✅ |
| Input Validation | ✅ |
| SQL Injection Protection | ✅ |
| Production Mode (no docs) | ✅ |
| Error Message Sanitization | ✅ |

### Ready for Railway

The backend is now secure and ready for deployment:

1. Set environment variables in Railway
2. Deploy with `railway up`
3. Verify health check passes
4. Verify `/docs` returns 404
5. Test rate limiting works

Your API is protected against:
- Brute force attacks (rate limiting)
- Unauthorized access (JWT auth)
- CORS abuse (origin whitelist)
- Information disclosure (production mode)
- Common web vulnerabilities (security headers)
