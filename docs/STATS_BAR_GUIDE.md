# Stats Bar Implementation Guide

## Overview

The stats bar shows real-time driver counts across the network. This guide covers implementation for different growth stages.

## API Endpoint

### GET /api/v1/map/stats/global

**Returns network-wide statistics (all active drivers)**

```bash
curl http://localhost:8000/api/v1/map/stats/global
```

**Response:**
```json
{
  "total_drivers": 1,
  "rolling": 0,
  "waiting": 1,
  "parked": 0,
  "recently_active": 1,
  "activity_percentage": 100.0,
  "timestamp": "2026-01-09T16:11:11.106475"
}
```

**Fields:**
- `total_drivers` - Total active drivers (active in last 12 hours)
- `rolling` - Drivers currently driving
- `waiting` - Drivers waiting for loads
- `parked` - Drivers parked/resting
- `recently_active` - Active in last hour (for freshness indicator)
- `activity_percentage` - % of drivers active in last hour
- `timestamp` - When stats were calculated

---

## Frontend Implementation

### Phase 1: Show Real Numbers (Current)

**Use real data from day one** - even if small. This builds authenticity.

```typescript
import { useEffect, useState } from 'react';

interface NetworkStats {
  total_drivers: number;
  rolling: number;
  waiting: number;
  parked: number;
  recently_active: number;
  activity_percentage: number;
  timestamp: string;
}

function StatsBar() {
  const [stats, setStats] = useState<NetworkStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();

    // Refresh every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadStats() {
    try {
      const response = await fetch('/api/v1/map/stats/global');
      const data = await response.json();
      setStats(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load stats:', error);
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="stats-bar">
        <div className="stat-item skeleton">Loading...</div>
      </div>
    );
  }

  if (!stats || stats.total_drivers === 0) {
    return (
      <div className="stats-bar">
        <div className="stat-item welcome">
          🚀 Be the first driver on the network!
        </div>
      </div>
    );
  }

  return (
    <div className="stats-bar">
      {stats.rolling > 0 && (
        <div className="stat-item rolling">
          <span className="icon">🚛</span>
          <span className="count">{formatNumber(stats.rolling)}</span>
          <span className="label">Rolling</span>
        </div>
      )}

      {stats.waiting > 0 && (
        <div className="stat-item waiting">
          <span className="icon">⏳</span>
          <span className="count">{formatNumber(stats.waiting)}</span>
          <span className="label">Waiting</span>
        </div>
      )}

      {stats.parked > 0 && (
        <div className="stat-item parked">
          <span className="icon">🅿️</span>
          <span className="count">{formatNumber(stats.parked)}</span>
          <span className="label">Parked</span>
        </div>
      )}

      {/* Optional: Activity indicator */}
      {stats.activity_percentage < 50 && (
        <div className="activity-indicator low">
          ⚠️ Network quiet
        </div>
      )}
    </div>
  );
}

function formatNumber(num: number): string {
  if (num < 1000) return num.toString();
  if (num < 10000) return `${(num / 1000).toFixed(1)}k`;
  return `${Math.round(num / 1000)}k`;
}

export default StatsBar;
```

---

## Display Strategy by Growth Stage

### Stage 1: 0 Drivers (Launch)
```
┌────────────────────────────────────┐
│  🚀 Be the first driver!            │
└────────────────────────────────────┘
```

### Stage 2: 1-9 Drivers (Early Adoption)
```
┌────────────────────────────────────┐
│  🚛 3 Rolling  ⏳ 2 Waiting  🅿️ 1 Parked │
└────────────────────────────────────┘
```
Show actual small numbers - this is fine! Users understand you're new.

### Stage 3: 10-99 Drivers (Growing)
```
┌────────────────────────────────────┐
│  🚛 12 Rolling  ⏳ 8 Waiting  🅿️ 5 Parked │
└────────────────────────────────────┘
```
Keep showing real numbers. This shows growth momentum.

### Stage 4: 100+ Drivers (Established)
```
┌────────────────────────────────────┐
│  🚛 1.2k Rolling  ⏳ 332 Waiting  🅿️ 891 Parked │
└────────────────────────────────────┘
```
Can abbreviate with "k" notation.

### Stage 5: 1000+ Drivers (Mature)
```
┌────────────────────────────────────┐
│  🚛 12.5k Rolling  ⏳ 3.3k Waiting  🅿️ 8.9k Parked │
└────────────────────────────────────┘
```

---

## Styling Examples

### Option 1: Pills (Your Current Design)

```css
.stats-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 24px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  font-size: 16px;
  font-weight: 600;
}

.stat-item.rolling {
  color: #10B981; /* Green */
}

.stat-item.waiting {
  color: #F59E0B; /* Orange */
}

.stat-item.parked {
  color: #EF4444; /* Red */
}

.stat-item .count {
  font-size: 20px;
  font-weight: 700;
}

.stat-item .label {
  font-size: 14px;
  opacity: 0.8;
}
```

### Option 2: Compact Bar

```typescript
function CompactStatsBar({ stats }: { stats: NetworkStats }) {
  return (
    <div className="compact-stats">
      <div className="stat">
        <span className="icon">🚛</span>
        <span className="value">{stats.rolling}</span>
      </div>
      <div className="divider">|</div>
      <div className="stat">
        <span className="icon">⏳</span>
        <span className="value">{stats.waiting}</span>
      </div>
      <div className="divider">|</div>
      <div className="stat">
        <span className="icon">🅿️</span>
        <span className="value">{stats.parked}</span>
      </div>
    </div>
  );
}
```

---

## Fun Empty States (When No Data)

### Early Launch Ideas

```typescript
const emptyStateMessages = [
  "🚀 Be the first driver on the network!",
  "👋 No drivers yet - be a pioneer!",
  "🌟 Launch day - join the first wave!",
  "🎯 Network starting up...",
  "📍 Waiting for drivers to check in...",
];

// Rotate messages
const message = emptyStateMessages[Math.floor(Math.random() * emptyStateMessages.length)];
```

### With Call-to-Action

```typescript
function EmptyStatsBar() {
  return (
    <div className="stats-bar empty">
      <div className="empty-state">
        <span className="icon">🚛</span>
        <span className="message">No drivers online yet</span>
        <button onClick={() => navigate('/check-in')}>
          Be the First 🚀
        </button>
      </div>
    </div>
  );
}
```

---

## Future: Phase 2 - Local Promotions

### With Ads (20% of time)

```typescript
function StatsBarWithAds({ stats }: { stats: NetworkStats }) {
  const [showAd, setShowAd] = useState(false);

  useEffect(() => {
    // Show ad 20% of the time
    const shouldShowAd = Math.random() < 0.2;
    setShowAd(shouldShowAd);
  }, []);

  if (showAd) {
    return (
      <div className="stats-bar ad">
        <img src="/logos/loves.png" className="sponsor-logo" />
        <span className="ad-text">
          ☕ 20% off coffee at Love's Travel Stops
        </span>
        <button className="cta-button">Find Location</button>
      </div>
    );
  }

  return <StatsBar stats={stats} />;
}
```

### Ad Rotation Examples

```typescript
const promotions = [
  {
    logo: '/logos/pilot.png',
    text: '⛽ Fuel rewards at Pilot Flying J',
    cta: 'Learn More',
    url: 'https://pilotflyingj.com'
  },
  {
    logo: '/logos/loves.png',
    text: '☕ 20% off coffee at Love\'s',
    cta: 'Find Location',
    url: '/facilities?brand=loves'
  },
  {
    logo: '/logos/ta-petro.png',
    text: '🚿 Free shower with fuel fill-up',
    cta: 'Details',
    url: 'https://ta-petro.com/deals'
  }
];
```

---

## Real-Time Updates

### WebSocket (Advanced - Future)

```typescript
import { useEffect, useState } from 'react';

function useRealtimeStats() {
  const [stats, setStats] = useState<NetworkStats | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/stats');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStats(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => ws.close();
  }, []);

  return stats;
}
```

### Polling (Simple - Current)

```typescript
function usePollingStats(intervalMs: number = 30000) {
  const [stats, setStats] = useState<NetworkStats | null>(null);

  useEffect(() => {
    async function fetchStats() {
      const response = await fetch('/api/v1/map/stats/global');
      const data = await response.json();
      setStats(data);
    }

    fetchStats();
    const interval = setInterval(fetchStats, intervalMs);
    return () => clearInterval(interval);
  }, [intervalMs]);

  return stats;
}
```

---

## Performance Optimization

### Caching Strategy

The stats endpoint is lightweight, but you can cache on the backend:

```python
# In app/routers/map.py

from functools import lru_cache
import time

_stats_cache = None
_stats_cache_time = 0
CACHE_DURATION = 30  # seconds

@router.get("/stats/global")
async def get_global_stats(db: Client = Depends(get_db_admin)):
    global _stats_cache, _stats_cache_time

    current_time = time.time()

    # Return cached result if less than 30 seconds old
    if _stats_cache and (current_time - _stats_cache_time) < CACHE_DURATION:
        return _stats_cache

    # Calculate fresh stats
    stats = calculate_stats(db)

    _stats_cache = stats
    _stats_cache_time = current_time

    return stats
```

---

## Testing

### Test with Current Data (1 driver)

```bash
curl http://localhost:8000/api/v1/map/stats/global
```

Expected:
```json
{
  "total_drivers": 1,
  "rolling": 0,
  "waiting": 1,
  "parked": 0
}
```

### Add Test Drivers for Development

```sql
-- Add 5 test drivers
INSERT INTO drivers (handle, avatar_id, status, user_id)
SELECT
  'test_driver_' || generate_series(1, 5),
  'bear',
  CASE (random() * 3)::int
    WHEN 0 THEN 'rolling'
    WHEN 1 THEN 'waiting'
    ELSE 'parked'
  END,
  (SELECT id FROM auth.users LIMIT 1);

-- Add locations for them
INSERT INTO driver_locations (driver_id, latitude, longitude, fuzzed_latitude, fuzzed_longitude, geohash)
SELECT
  id,
  36.8 + (random() * 0.2),
  -119.9 + (random() * 0.2),
  36.8 + (random() * 0.2),
  -119.9 + (random() * 0.2),
  '9qd9'
FROM drivers
WHERE handle LIKE 'test_driver_%';
```

Now stats will show:
```json
{
  "total_drivers": 6,
  "rolling": 2,
  "waiting": 3,
  "parked": 1
}
```

---

## Recommendations

### ✅ Do This

1. **Show real numbers from day 1** - Authenticity > fake numbers
2. **Update every 30-60 seconds** - Fresh but not excessive
3. **Hide 0 counts** - Only show statuses with drivers
4. **Add empty state message** - "Be the first driver!"
5. **Abbreviate at 1000+** - "1.2k" instead of "1,234"

### ❌ Don't Do This

1. **Don't fake numbers** - Users will catch you
2. **Don't update too fast** - <10 seconds is excessive
3. **Don't show decimal precision** - "1,234" not "1,234.5"
4. **Don't make it too prominent** - Subtle top bar is enough

---

## Growth Milestones

Celebrate these in the UI:

- **First 10 drivers** - "Network launched! 10 drivers online"
- **First 100 drivers** - "100+ drivers on the network!"
- **First 1,000 drivers** - "1k+ drivers - we're growing fast!"
- **First 10,000 drivers** - "10k drivers nationwide 🎉"

---

## Summary

**API:** `GET /api/v1/map/stats/global`

**Update frequency:** 30 seconds

**Display:** Show real numbers, even if small

**Empty state:** "🚀 Be the first driver!"

**Future:** Add local promotions (Phase 2)
