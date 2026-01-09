-- Sample Facilities Data
-- Use this as a template for importing real facility data

-- Example 1: Pilot Travel Center
INSERT INTO facilities (
    name, type, latitude, longitude, address, city, state, zip_code,
    phone, brand, amenities, parking_spaces, is_open_24h
) VALUES (
    'Pilot Travel Center #456',
    'truck_stop',
    34.0522,
    -118.2437,
    '123 Highway 99',
    'Bakersfield',
    'CA',
    '93308',
    '661-555-0123',
    'Pilot Flying J',
    '{"fuel": true, "diesel": true, "showers": true, "restaurant": true, "wifi": true, "laundry": true, "atm": true}',
    75,
    true
);

-- Example 2: Love's Travel Stop
INSERT INTO facilities (
    name, type, latitude, longitude, address, city, state, zip_code,
    phone, brand, amenities, parking_spaces, is_open_24h
) VALUES (
    'Love''s Travel Stop #789',
    'truck_stop',
    35.4676,
    -97.5164,
    '456 I-40 Exit 123',
    'Oklahoma City',
    'OK',
    '73109',
    '405-555-0456',
    'Love''s',
    '{"fuel": true, "diesel": true, "showers": true, "restaurant": true, "wifi": true, "dog_park": true, "scales": true}',
    100,
    true
);

-- Example 3: Rest Area
INSERT INTO facilities (
    name, type, latitude, longitude, address, city, state, zip_code,
    amenities, parking_spaces, is_open_24h
) VALUES (
    'I-80 Rest Area - Eastbound',
    'rest_area',
    41.2565,
    -95.9345,
    'I-80 Mile Marker 432',
    'Omaha',
    'NE',
    '68102',
    '{"restrooms": true, "vending": true, "picnic": true, "wifi": false}',
    50,
    true
);

-- Example 4: TA Petro
INSERT INTO facilities (
    name, type, latitude, longitude, address, city, state, zip_code,
    phone, brand, amenities, parking_spaces, is_open_24h
) VALUES (
    'TA Petro Stopping Center',
    'truck_stop',
    39.7392,
    -104.9903,
    '789 I-70 Service Road',
    'Denver',
    'CO',
    '80202',
    '303-555-0789',
    'TA Petro',
    '{"fuel": true, "diesel": true, "showers": true, "restaurant": true, "wifi": true, "laundry": true, "truck_wash": true, "maintenance": true}',
    120,
    true
);

-- Example 5: Truck Parking Area
INSERT INTO facilities (
    name, type, latitude, longitude, address, city, state, zip_code,
    amenities, parking_spaces, is_open_24h
) VALUES (
    'Safe Haven Truck Parking',
    'parking',
    33.4484,
    -112.0740,
    '321 Industrial Blvd',
    'Phoenix',
    'AZ',
    '85003',
    '{"security": true, "lighting": true, "restrooms": true}',
    40,
    true
);
