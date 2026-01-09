"""
Location Utility Functions
Helper functions for location fuzzing, distance calculation, and geospatial operations
"""

import random
import math
from typing import Tuple


def fuzz_location(latitude: float, longitude: float, radius_miles: float) -> Tuple[float, float]:
    """
    Apply privacy fuzzing to a location by adding random offset within radius.

    Args:
        latitude: Original latitude
        longitude: Original longitude
        radius_miles: Fuzzing radius in miles

    Returns:
        Tuple of (fuzzed_latitude, fuzzed_longitude)
    """
    # Convert miles to degrees (approximate)
    # 1 degree latitude ≈ 69 miles
    # 1 degree longitude varies by latitude
    radius_lat = radius_miles / 69.0
    radius_lng = radius_miles / (69.0 * math.cos(math.radians(latitude)))

    # Generate random angle and distance
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, 1)  # Random distance within radius

    # Apply offset
    fuzzed_lat = latitude + (radius_lat * distance * math.cos(angle))
    fuzzed_lng = longitude + (radius_lng * distance * math.sin(angle))

    return fuzzed_lat, fuzzed_lng


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate

    Returns:
        Distance in miles
    """
    # Earth radius in miles
    R = 3959.0

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2

    c = 2 * math.asin(math.sqrt(a))

    distance = R * c

    return distance


def get_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing between two coordinates.

    Args:
        lat1, lon1: Start coordinate
        lat2, lon2: End coordinate

    Returns:
        Bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)

    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360

    return bearing


def is_location_stale(recorded_at: str, max_age_hours: int = 12) -> bool:
    """
    Check if a location is stale (too old).

    Args:
        recorded_at: ISO datetime string
        max_age_hours: Maximum age in hours

    Returns:
        True if location is stale
    """
    from datetime import datetime, timedelta

    recorded = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    age = datetime.utcnow() - recorded.replace(tzinfo=None)

    return age > timedelta(hours=max_age_hours)


def get_geohash_neighbors(geohash: str) -> list[str]:
    """
    Get neighboring geohash cells (for searching nearby areas).

    Args:
        geohash: Geohash string

    Returns:
        List of neighbor geohash strings
    """
    import geohash as gh

    # Decode geohash to coordinates
    lat, lng = gh.decode(geohash)

    # Calculate approximate cell size at this precision
    precision = len(geohash)
    cell_size_degrees = 180 / (2 ** (precision * 2.5))  # Approximate

    # Generate neighbors
    neighbors = []
    for dlat in [-1, 0, 1]:
        for dlng in [-1, 0, 1]:
            if dlat == 0 and dlng == 0:
                neighbors.append(geohash)
            else:
                neighbor_lat = lat + (dlat * cell_size_degrees)
                neighbor_lng = lng + (dlng * cell_size_degrees)
                neighbor_hash = gh.encode(neighbor_lat, neighbor_lng, precision=precision)
                neighbors.append(neighbor_hash)

    return neighbors
