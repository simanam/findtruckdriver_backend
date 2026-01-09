# Deployment Guide

## Production Deployment Checklist

### 1. Database Setup (Supabase)

#### Initial Setup

1. **Create Supabase Project**
   - Go to https://supabase.com/dashboard
   - Create new project
   - Wait for database provisioning

2. **Run Migrations**
   ```bash
   # Set production DATABASE_URL in .env
   export DATABASE_URL="postgresql://postgres:..."

   # Run migrations
   ./migrations/run_migrations.sh
   ```

3. **Verify Tables Created**
   - Check Supabase Dashboard → Table Editor
   - Should see: `drivers`, `driver_locations`, `status_history`, `migration_history`

4. **Enable PostGIS**
   - Should be auto-enabled by migration
   - Verify: Database → Extensions → PostGIS should be enabled

#### Database Checklist

- [ ] Supabase project created
- [ ] DATABASE_URL added to environment
- [ ] Migrations run successfully
- [ ] All tables exist
- [ ] PostGIS extension enabled
- [ ] RLS policies active
- [ ] Indexes created

### 2. Environment Variables

#### Required Variables

```bash
# Supabase
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY="eyJhbG..."
SUPABASE_SECRET_KEY="eyJhbG..."
DATABASE_URL="postgresql://postgres:..."

# API
API_HOST="0.0.0.0"
API_PORT="8000"
API_PREFIX="/api/v1"

# Security
SECRET_KEY="your-secret-key-here"  # Generate with: openssl rand -hex 32
ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

# Location Privacy
LOCATION_FUZZ_ROLLING_MILES="2.0"
LOCATION_FUZZ_WAITING_MILES="1.0"
LOCATION_FUZZ_PARKED_MILES="0.5"

# Redis (optional)
REDIS_URL="redis://localhost:6379"

# Monitoring (optional)
SENTRY_DSN="https://..."
```

### 3. Deployment Options

#### Option A: Fly.io (Recommended)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
fly launch --name findtruckdriver-api

# Set secrets
fly secrets set SUPABASE_URL="..."
fly secrets set SUPABASE_PUBLISHABLE_KEY="..."
fly secrets set SUPABASE_SECRET_KEY="..."
fly secrets set DATABASE_URL="..."
fly secrets set SECRET_KEY="$(openssl rand -hex 32)"

# Deploy
fly deploy
```

#### Option B: Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Set environment variables in Railway dashboard

# Deploy
railway up
```

#### Option C: Docker + Any Cloud

```bash
# Build image
docker build -t findtruckdriver-api .

# Run locally
docker run -p 8000:8000 --env-file .env findtruckdriver-api

# Push to registry
docker tag findtruckdriver-api your-registry/findtruckdriver-api
docker push your-registry/findtruckdriver-api

# Deploy to cloud (AWS/GCP/Azure)
```

### 4. Post-Deployment

#### Health Check

```bash
curl https://your-api.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T...",
  "database": "connected",
  "cache": "connected"
}
```

#### Test Authentication

```bash
# Request OTP
curl -X POST https://your-api.com/api/v1/auth/email/otp/request \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Should receive email with OTP code
```

#### Monitor Logs

```bash
# Fly.io
fly logs

# Railway
railway logs

# Docker
docker logs container-name
```

### 5. Database Migrations (Future)

When adding new features, create new migration files:

```bash
# Create migration file
touch migrations/003_add_new_feature.sql

# Write SQL migration
# ...

# Test locally first
./migrations/run_migrations.sh

# Deploy to production
git push  # Triggers auto-deploy with migrations
```

### 6. Monitoring Setup (Optional)

#### Sentry for Error Tracking

1. Create Sentry project
2. Add SENTRY_DSN to environment
3. Errors will be automatically tracked

#### Uptime Monitoring

- Use UptimeRobot or similar
- Monitor: `https://your-api.com/health`
- Alert on downtime

### 7. Production Checklist

#### Security

- [ ] HTTPS enabled (required for production)
- [ ] CORS configured with allowed domains
- [ ] Rate limiting enabled
- [ ] SQL injection protection (use parameterized queries)
- [ ] Input validation with Pydantic
- [ ] Secrets not in code/git

#### Performance

- [ ] Database indexes created (via migrations)
- [ ] Connection pooling configured
- [ ] Redis cache enabled (optional)
- [ ] CDN for static assets (if any)

#### Reliability

- [ ] Health check endpoint working
- [ ] Error logging configured
- [ ] Backup strategy (Supabase handles this)
- [ ] Rollback plan documented

#### Documentation

- [ ] API docs accessible: `/docs`
- [ ] Environment variables documented
- [ ] Migration process documented
- [ ] Contact for issues documented

### 8. Rollback Procedure

If deployment fails:

```bash
# Fly.io
fly releases
fly rollback <version>

# Railway
railway rollback

# Manual rollback
git revert HEAD
git push
```

Database rollback:
```bash
# Create reverse migration
# Example: 004_rollback_003.sql

# Apply manually
psql $DATABASE_URL -f migrations/004_rollback_003.sql
```

### 9. Scaling

#### Horizontal Scaling

```bash
# Fly.io
fly scale count 3

# Railway
# Scale in dashboard
```

#### Database Performance

- Monitor slow queries in Supabase dashboard
- Add indexes as needed
- Consider read replicas (Supabase Pro plan)

### 10. Cost Estimation

**Free Tier:**
- Supabase: Free up to 500MB database, 2GB bandwidth
- Fly.io: 3 shared-cpu-1x VMs free
- Total: ~$0/month for low traffic

**Production (Medium Traffic):**
- Supabase Pro: $25/month
- Fly.io: ~$20/month (2 VMs)
- Total: ~$45/month

---

## Quick Deploy Commands

```bash
# 1. Setup database
./migrations/run_migrations.sh

# 2. Deploy to Fly.io
fly deploy

# 3. Check health
curl https://your-api.fly.dev/health

# 4. Done! 🚀
```

---

## Support

For deployment issues:
- Check logs first
- Verify environment variables
- Test migrations locally
- Contact: [your-email]
