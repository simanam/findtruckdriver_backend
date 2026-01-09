# Error Tracker
**Find a Truck Driver - Backend Error Documentation**

This file documents all errors, bugs, and issues encountered during development, along with their solutions.

---

## How to Use This File

### For New Errors
1. Create a new entry with unique ID (ERR-YYYYMMDD-NNN)
2. Document the error details
3. Track investigation and resolution
4. Mark as resolved when fixed

### Severity Levels
- 🔴 **Critical**: System down, data loss, security breach
- 🟠 **High**: Major feature broken, performance severely degraded
- 🟡 **Medium**: Feature partially broken, workaround exists
- 🟢 **Low**: Minor issue, cosmetic, edge case

### Status
- 🆕 **New**: Just discovered, not yet investigated
- 🔍 **Investigating**: Active investigation in progress
- 🔨 **In Progress**: Fix being implemented
- ✅ **Resolved**: Fixed and verified
- ⏸️ **Deferred**: Will fix later, not blocking
- 🚫 **Won't Fix**: Decided not to fix (document why)

---

## Error Log

### Template

```markdown
### ERR-YYYYMMDD-001: [Brief Error Title]

**Severity**: [🔴/🟠/🟡/🟢]
**Status**: [🆕/🔍/🔨/✅/⏸️/🚫]
**Discovered**: YYYY-MM-DD HH:MM UTC
**Resolved**: YYYY-MM-DD HH:MM UTC (if applicable)

**Component**: [e.g., Auth Service, Location API, Database]
**Environment**: [Local/Staging/Production]

**Description**:
[Detailed description of the error]

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Error Message/Stack Trace**:
```
[Paste error message or stack trace here]
```

**Impact**:
- [Who/what is affected]
- [Severity of impact]

**Investigation Notes**:
- [Date Time]: [Finding or attempt]
- [Date Time]: [Finding or attempt]

**Root Cause**:
[What was the actual cause of the error]

**Solution**:
[How the error was fixed]

**Prevention**:
[How to prevent this from happening again]

**Related Errors**:
- ERR-YYYYMMDD-XXX
- ERR-YYYYMMDD-YYY

**References**:
- [Link to code]
- [Link to documentation]
- [Link to external resources]
```

---

## Active Errors

*No active errors at this time.*

---

## Resolved Errors

*No resolved errors yet.*

---

## Deferred Errors

*No deferred errors yet.*

---

## Known Limitations

Document non-error limitations of the system that developers should be aware of.

### LIM-001: Location Update Frequency
**Component**: Location Service
**Description**: Location updates limited to once per minute per driver to prevent database overload
**Impact**: Real-time tracking may show 1-minute lag
**Workaround**: Acceptable for MVP, may optimize in future
**Status**: By Design

---

## Error Categories

### Authentication Errors (AUTH-XXX)
*Errors related to authentication, authorization, tokens*

### Database Errors (DB-XXX)
*Errors related to database connections, queries, transactions*

### API Errors (API-XXX)
*Errors related to API endpoints, request/response handling*

### Real-Time Errors (RT-XXX)
*Errors related to WebSockets, broadcasting, subscriptions*

### Performance Errors (PERF-XXX)
*Errors related to slow queries, timeouts, resource exhaustion*

### Data Integrity Errors (DATA-XXX)
*Errors related to data validation, corruption, inconsistency*

### Security Errors (SEC-XXX)
*Errors related to security vulnerabilities, unauthorized access*

### Integration Errors (INT-XXX)
*Errors related to third-party integrations (Supabase, Redis, etc.)*

---

## Common Error Patterns

### Pattern 1: Connection Pool Exhaustion
**Symptoms**: Timeouts, "Too many connections" errors
**Common Causes**: Not closing connections, connection leaks
**Debug Steps**:
1. Check connection pool size
2. Review async context managers
3. Look for missing `finally` blocks
**Prevention**: Always use context managers for database connections

### Pattern 2: Race Conditions in Stats Updates
**Symptoms**: Incorrect counts, duplicate entries
**Common Causes**: Concurrent updates without locks
**Debug Steps**:
1. Check Redis transaction boundaries
2. Look for missing WATCH commands
3. Review order of operations
**Prevention**: Use Redis transactions or optimistic locking

### Pattern 3: Geohash Precision Issues
**Symptoms**: Drivers not appearing in expected regions
**Common Causes**: Wrong precision level, boundary edge cases
**Debug Steps**:
1. Verify geohash calculation
2. Check precision level (2 for regions, 4 for clusters, etc.)
3. Test with boundary coordinates
**Prevention**: Unit test geohash functions thoroughly

---

## Error Response Standards

All API errors should follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    },
    "request_id": "unique-request-id",
    "timestamp": "2026-01-08T18:50:00Z"
  }
}
```

### Standard Error Codes

#### Authentication (4xx)
- `AUTH_REQUIRED` (401): Authentication required
- `AUTH_INVALID` (401): Invalid credentials
- `AUTH_EXPIRED` (401): Token expired
- `AUTH_FORBIDDEN` (403): Insufficient permissions

#### Validation (4xx)
- `VALIDATION_ERROR` (400): Input validation failed
- `INVALID_COORDINATES` (400): Invalid lat/lng
- `INVALID_STATUS` (400): Invalid status value
- `HANDLE_TAKEN` (409): Handle already exists
- `RATE_LIMIT_EXCEEDED` (429): Too many requests

#### Server Errors (5xx)
- `INTERNAL_ERROR` (500): Unexpected server error
- `DATABASE_ERROR` (500): Database connection/query error
- `REDIS_ERROR` (500): Redis connection error
- `EXTERNAL_SERVICE_ERROR` (502): Third-party service error

#### Not Found (4xx)
- `DRIVER_NOT_FOUND` (404): Driver does not exist
- `FACILITY_NOT_FOUND` (404): Facility does not exist
- `ENDPOINT_NOT_FOUND` (404): Invalid endpoint

---

## Debugging Tools & Commands

### Check Redis Connection
```bash
redis-cli ping
```

### Check Database Connection
```bash
psql $DATABASE_URL -c "SELECT 1"
```

### Check API Health
```bash
curl http://localhost:8000/health
```

### View Recent Logs
```bash
tail -f logs/app.log
```

### Monitor Performance
```bash
# Check slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

---

## Incident Response Checklist

When a critical error occurs in production:

- [ ] 1. Alert team immediately
- [ ] 2. Document error in this file (ERR-YYYYMMDD-XXX)
- [ ] 3. Check error logs and metrics
- [ ] 4. Determine impact and affected users
- [ ] 5. Implement immediate workaround if possible
- [ ] 6. Communicate status to stakeholders
- [ ] 7. Fix root cause
- [ ] 8. Deploy fix
- [ ] 9. Verify resolution
- [ ] 10. Conduct post-mortem
- [ ] 11. Update documentation
- [ ] 12. Add preventive measures

---

## Post-Mortem Template

```markdown
## Post-Mortem: [Incident Title]

**Date**: YYYY-MM-DD
**Duration**: X hours/minutes
**Severity**: [Critical/High/Medium]

**Timeline**:
- HH:MM - [Event]
- HH:MM - [Event]

**What Happened**:
[Detailed description]

**Root Cause**:
[What actually caused the issue]

**Impact**:
- Users affected: X
- Downtime: X minutes
- Data loss: Yes/No

**What Went Well**:
- [Positive aspect]

**What Went Wrong**:
- [Negative aspect]

**Action Items**:
- [ ] [Preventive measure 1]
- [ ] [Preventive measure 2]

**Lessons Learned**:
[Key takeaways]
```

---

*Last Updated: 2026-01-08 18:50 UTC*
*Total Active Errors: 0*
*Total Resolved Errors: 0*
