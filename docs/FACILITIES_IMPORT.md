# Facilities Data Import Guide

## Overview

The `facilities` table stores truck stops, rest areas, and parking locations. This guide explains how to populate it with data.

## Table Structure

```sql
facilities (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- "Pilot Travel Center #456"
    type VARCHAR(50) NOT NULL,               -- truck_stop, rest_area, parking, service_plaza, weigh_station
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    address TEXT,                            -- Street address
    city VARCHAR(100),
    state VARCHAR(2),                        -- Two-letter state code
    zip_code VARCHAR(10),
    country VARCHAR(2) DEFAULT 'US',
    phone VARCHAR(20),
    website TEXT,
    amenities JSONB DEFAULT '{}',            -- {"fuel": true, "showers": true, ...}
    parking_spaces INT,                      -- Number of truck parking spots
    is_open_24h BOOLEAN DEFAULT false,
    brand VARCHAR(100),                      -- "Pilot Flying J", "Love's", "TA Petro"
    geohash VARCHAR(12),                     -- For spatial clustering (can be null)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
```

## Data Sources

### Option 1: Public Datasets (Free)

1. **OpenStreetMap** - Community-maintained map data
   - API: https://overpass-api.de/
   - Query for amenities like `amenity=fuel` + `hgv=yes` (heavy goods vehicles)
   - Export to JSON/CSV
   - Pros: Free, worldwide coverage
   - Cons: Data quality varies by region

2. **U.S. DOT Rest Areas** - Official government data
   - Dataset: https://data.gov or state DOT websites
   - Pros: Accurate for rest areas
   - Cons: Limited to rest areas, doesn't include private truck stops

3. **Truck Parking Information Management System (TPIMS)**
   - Some states publish parking availability data
   - Pros: Real-time parking counts
   - Cons: Only available in participating states

### Option 2: Commercial APIs (Paid)

1. **TruckMaster** - Comprehensive truck stop database
   - Website: https://truckmaster.com
   - Coverage: All major brands (Pilot, Love's, TA, etc.)
   - Cost: ~$500-1000/year for API access

2. **DAT Freight & Analytics** - Trucking industry data
   - Includes truck stop locations
   - Cost: Enterprise pricing

3. **Google Places API** - Search for truck stops
   - Query: "truck stop near [location]"
   - Cost: Pay per API call
   - Pros: Easy to integrate
   - Cons: May miss some locations, expensive at scale

### Option 3: Web Scraping (Legal Caution)

1. **Pilot Flying J Locations** - https://pilotflyingj.com/locations
2. **Love's Travel Stops** - https://www.loves.com/locations
3. **TA Petro** - https://ta-petro.com/locations

⚠️ **Important**: Check each website's Terms of Service before scraping. Many prohibit automated access.

### Option 4: Manual Entry (Small Scale)

Use the sample data template for initial testing:

```bash
psql $DATABASE_URL -f migrations/sample_facilities.sql
```

## Import Methods

### Method 1: SQL Insert (Recommended for < 1000 records)

```bash
# Load sample data
psql $DATABASE_URL -f migrations/sample_facilities.sql

# Or create your own SQL file
psql $DATABASE_URL -f your_facilities_data.sql
```

### Method 2: CSV Import (Recommended for 1000+ records)

1. **Prepare CSV file** (`facilities.csv`):
```csv
name,type,latitude,longitude,address,city,state,zip_code,phone,brand,parking_spaces,is_open_24h,amenities
"Pilot Travel Center #456","truck_stop",34.0522,-118.2437,"123 Highway 99","Bakersfield","CA","93308","661-555-0123","Pilot Flying J",75,true,"{\"fuel\": true, \"showers\": true}"
```

2. **Import CSV**:
```bash
psql $DATABASE_URL -c "\COPY facilities(name,type,latitude,longitude,address,city,state,zip_code,phone,brand,parking_spaces,is_open_24h,amenities) FROM 'facilities.csv' CSV HEADER"
```

### Method 3: Python Script (Recommended for API imports)

Create `import_facilities.py`:

```python
import os
from supabase import create_client, Client

# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase: Client = create_client(url, key)

# Sample facility data
facilities = [
    {
        "name": "Pilot Travel Center #456",
        "type": "truck_stop",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "address": "123 Highway 99",
        "city": "Bakersfield",
        "state": "CA",
        "zip_code": "93308",
        "phone": "661-555-0123",
        "brand": "Pilot Flying J",
        "amenities": {
            "fuel": True,
            "diesel": True,
            "showers": True,
            "restaurant": True,
            "wifi": True,
        },
        "parking_spaces": 75,
        "is_open_24h": True,
    },
    # Add more facilities...
]

# Import
for facility in facilities:
    result = supabase.table("facilities").insert(facility).execute()
    print(f"Imported: {facility['name']}")
```

Run:
```bash
python import_facilities.py
```

### Method 4: OpenStreetMap Import (Advanced)

```python
import overpy
import os
from supabase import create_client

# Query Overpass API for truck stops
api = overpy.Overpass()
query = """
[out:json];
area["ISO3166-1"="US"][admin_level=2];
(
  node["amenity"="fuel"]["hgv"="yes"](area);
  node["amenity"="parking"]["parking"="surface"]["hgv"="yes"](area);
);
out body;
"""

result = api.query(query)

# Initialize Supabase
supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SECRET_KEY")
)

# Import nodes
for node in result.nodes:
    facility = {
        "name": node.tags.get("name", "Unknown"),
        "type": "truck_stop" if node.tags.get("amenity") == "fuel" else "parking",
        "latitude": float(node.lat),
        "longitude": float(node.lon),
        "address": node.tags.get("addr:street"),
        "city": node.tags.get("addr:city"),
        "state": node.tags.get("addr:state"),
        "zip_code": node.tags.get("addr:postcode"),
        "phone": node.tags.get("phone"),
        "brand": node.tags.get("brand"),
        "amenities": {},
    }

    # Add amenities
    if node.tags.get("shower") == "yes":
        facility["amenities"]["showers"] = True
    if node.tags.get("restaurant") == "yes":
        facility["amenities"]["restaurant"] = True

    supabase.table("facilities").insert(facility).execute()
    print(f"Imported: {facility['name']}")
```

## Testing the Import

After importing, verify data:

```bash
# Count facilities
psql $DATABASE_URL -c "SELECT COUNT(*) FROM facilities;"

# View sample
psql $DATABASE_URL -c "SELECT name, type, city, state FROM facilities LIMIT 10;"

# Check by type
psql $DATABASE_URL -c "SELECT type, COUNT(*) FROM facilities GROUP BY type;"

# Find facilities near a location (example: within ~50 miles of 34.05, -118.24)
psql $DATABASE_URL -c "
SELECT name, city, state,
       SQRT(POW(69.1 * (latitude - 34.05), 2) + POW(69.1 * (-118.24 - longitude) * COS(latitude / 57.3), 2)) AS distance_miles
FROM facilities
WHERE SQRT(POW(69.1 * (latitude - 34.05), 2) + POW(69.1 * (-118.24 - longitude) * COS(latitude / 57.3), 2)) < 50
ORDER BY distance_miles
LIMIT 10;
"
```

## Using Facilities in the App

Once imported, the app-open endpoint will automatically show facility names:

```json
{
  "action": "prompt_status",
  "reason": "welcome_back",
  "message": "Welcome back! What's your status?",
  "current_status": "parked",
  "last_location_name": "Pilot Travel Center #456",
  "hours_since_update": 14.5
}
```

## Data Maintenance

### Update Facility Data

```bash
# Update a facility
psql $DATABASE_URL -c "
UPDATE facilities
SET parking_spaces = 100, updated_at = NOW()
WHERE name = 'Pilot Travel Center #456';
"
```

### Delete Test Data

```bash
# Clear all facilities
psql $DATABASE_URL -c "TRUNCATE facilities;"
```

## Recommended Approach

**For MVP/Testing:**
1. Start with `sample_facilities.sql` (5 test locations)
2. Manually add 20-50 major truck stops along popular routes (I-80, I-40, I-10)

**For Production:**
1. Purchase TruckMaster API access (~$500-1000/year)
2. Import all major chains (Pilot, Love's, TA, etc.)
3. Set up monthly sync to keep data fresh

**For Future:**
1. Add user-submitted locations
2. Real-time parking availability
3. User reviews and ratings

## Cost Comparison

| Method | Cost | Records | Effort |
|--------|------|---------|--------|
| Manual Entry | $0 | 50-100 | High |
| OpenStreetMap | $0 | 5,000+ | Medium |
| Web Scraping | $0 | 10,000+ | High |
| TruckMaster API | $500-1000/yr | 50,000+ | Low |
| Google Places API | $0.017/query | Variable | Medium |

## Next Steps

1. Start with sample data for testing
2. Choose a data source based on budget
3. Import initial dataset
4. Test app-open endpoint shows location names
5. Set up data refresh schedule

## Questions?

See the main [DATABASE_TABLES.md](DATABASE_TABLES.md) for more context on the facilities table.
