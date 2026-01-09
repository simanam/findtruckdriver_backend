# Follow-Up Questions V2 - Ask on Entry

## The Key Insight

**Drivers use the app when they STOP, not when they START moving.**

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ROLLING          PARKED              WAITING                   │
│  ───────          ──────              ───────                   │
│                                                                 │
│  👀 Eyes on road  📱 Phone in hand    📱 Phone in hand          │
│  🚫 Don't bother  ✅ CAPTURE NOW      ✅ CAPTURE NOW             │
│  ⏱️ No time       ⏱️ Has time         ⏱️ Bored, has time        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## V2 Flow: Ask on ENTRY

### 1. → PARKED

**When:** Driver just pulled into a spot
**Phone:** In hand, app is open
**Can assess:** YES - they can see the spot immediately

**Question:**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Status: PARKED                                                 │
│  Love's Truck Stop                                              │
│                                                                 │
│  How's the spot?                                                │
│                                                                 │
│       ┌─────────┐  ┌─────────┐  ┌─────────┐                    │
│       │ 😴      │  │ 😐      │  │ 😬      │                    │
│       │ Solid   │  │ Meh     │  │ Sketch  │                    │
│       └─────────┘  └─────────┘  └─────────┘                    │
│                                                                 │
│                          Skip →                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Captured:**
- Parking spot safety rating
- Real-time assessment
- Helps other drivers pick safe spots

**Example Insights:**
- "Love's Truck Stop: 94% say Solid"
- "Avoid this rest area at night: 67% say Sketch"

---

### 2. → WAITING

**When:** Driver just arrived at facility
**Phone:** In hand, app is open
**Can assess:** YES - they can see the dock/line situation

**Question:**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Status: WAITING                                                │
│  Sysco Distribution Center                                      │
│                                                                 │
│  How's it looking?                                              │
│                                                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │ 🏃      │ │ 🐢      │ │ 🧊      │ │ 🤷      │               │
│  │ Moving  │ │ Slow    │ │ Dead    │ │ Just    │               │
│  │         │ │         │ │         │ │ got here│               │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘               │
│                                                                 │
│                          Skip →                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Captured:**
- Real-time facility flow
- Current conditions
- Helps drivers avoid slow facilities

**Example Insights:**
- "Sysco Distribution: Currently 🧊 Dead (3 reports in last hour)"
- "This facility is usually 🏃 Moving in mornings"

---

### 3. → ROLLING (from PARKED)

**When:** Driver is about to start driving
**Phone:** May be put down
**Question:** Just encouragement

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Drive safe! 🚛                                                 │
│                                                                 │
│       [ Auto-dismisses in 2 seconds ]                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Captured:** Nothing (driver needs to focus)

---

### 4. → ROLLING (from WAITING)

**When:** Driver is loaded and ready to leave
**Phone:** May be put down
**Question:** Depends on wait time

#### If waited < 1 hour:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  47 min - Quick one! 🙌                                         │
│                                                                 │
│       [ Auto-dismisses in 2 seconds ]                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### If waited 1-2 hours:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1 hr 23 min - Not bad!                                         │
│                                                                 │
│       [ Auto-dismisses in 2 seconds ]                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### If waited 2+ hours:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  3 hrs 22 min. Getting paid?                                    │
│  Sysco Distribution                                             │
│                                                                 │
│       ┌─────────┐          ┌─────────┐                          │
│       │ 💰      │          │ 😤      │                          │
│       │ Yep     │          │ Nope    │                          │
│       └─────────┘          └─────────┘                          │
│                                                                 │
│                          Skip →                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why ask on ROLLING for detention?**
- This data is TOO VALUABLE to skip
- Drivers WANT to report unpaid detention
- It's quick (2 taps)
- Only asked for 2+ hour waits

**Data Captured:**
- Wait time (calculated automatically)
- Whether detention was paid
- Facility accountability

**Example Insights:**
- "Sysco Houston: 23% detention pay rate (47 reports)"
- "Walmart DC #6345: 89% pay detention (12 reports)"

---

## Complete Flow Matrix

| Status Change | When | Question | Response Time | Data Value |
|---------------|------|----------|---------------|------------|
| → PARKED | Entry | "How's the spot?" | 1 tap | Spot safety |
| → WAITING | Entry | "How's it looking?" | 1 tap | Facility flow |
| → ROLLING (from PARKED) | Exit | "Drive safe! 🚛" | Auto-dismiss | None |
| → ROLLING (from WAITING, <1hr) | Exit | "Quick one! 🙌" | Auto-dismiss | Time only |
| → ROLLING (from WAITING, 1-2hr) | Exit | "Not bad!" | Auto-dismiss | Time only |
| → ROLLING (from WAITING, 2+hr) | Exit | "Getting paid?" | 1 tap | Time + payment |

---

## Why This Works

### 1. **Maximum Engagement**
- Ask when driver is actively using app
- Phone is in hand, not driving
- They have time to answer

### 2. **Immediate Assessment**
- PARKED: Can see if spot is sketchy RIGHT NOW
- WAITING: Can see if line is moving RIGHT NOW
- Not asking them to remember later

### 3. **Minimal Friction on ROLLING**
- Just encouragement + auto-dismiss
- Exception: Detention pay (too valuable)
- Driver can focus on driving

### 4. **Data Quality**
- Spot safety: Fresh, accurate
- Facility flow: Real-time conditions
- Detention: Precise times + payment status

---

## Implementation

The backend automatically determines which question to ask:

```python
# → PARKED: Always ask
if new_status == "parked":
    return "How's the spot?"  # 😴 Solid / 😐 Meh / 😬 Sketch

# → WAITING: Always ask
if new_status == "waiting":
    return "How's it looking?"  # 🏃 Moving / 🐢 Slow / 🧊 Dead / 🤷 Just here

# → ROLLING: Minimal
if new_status == "rolling":
    if prev_status == "parked":
        return "Drive safe! 🚛"  # Auto-dismiss
    elif prev_status == "waiting":
        if wait_time < 2_hours:
            return "Quick one! 🙌"  # Auto-dismiss
        else:
            return "Getting paid?"  # 💰 Yep / 😤 Nope
```

---

## Frontend Integration

The response includes `follow_up_question` when appropriate:

```json
{
  "status_update_id": "uuid",
  "status": "parked",
  "follow_up_question": {
    "question_type": "parking_spot_entry",
    "text": "How's the spot?",
    "subtext": "Love's Truck Stop",
    "options": [
      {"emoji": "😴", "label": "Solid", "value": "solid"},
      {"emoji": "😐", "label": "Meh", "value": "meh"},
      {"emoji": "😬", "label": "Sketch", "value": "sketch"}
    ],
    "skippable": true
  }
}
```

Display immediately after status update confirmation.

---

## Data Value

### Parking Safety Ratings
- "Love's Truck Stop: 94% Solid (127 ratings)"
- "Rest Area I-80 Mile 142: 67% Sketch (43 ratings)"
- Sort by safety when finding parking

### Real-Time Facility Flow
- "Sysco Distribution: Currently 🧊 Dead (5 reports in last hour)"
- "Walmart DC: Usually 🏃 Moving in mornings"
- Avoid slow facilities, plan arrival times

### Detention Accountability
- "Sysco Houston: 23% pay detention (47 drivers)"
- "Target DC: 91% pay detention (18 drivers)"
- Industry-changing transparency

---

## The Simplicity

```
PARKED?   →  "How's the spot?"      →  One tap
WAITING?  →  "How's it looking?"    →  One tap
ROLLING?  →  "Drive safe!" OR       →  Auto-dismiss
             "Getting paid?" (2+hrs) →  One tap (if long wait)
```

Three core questions. Captured at exactly the right moment. Maximum value, minimum friction.
