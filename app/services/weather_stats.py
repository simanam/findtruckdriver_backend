"""
Weather Stats Service
Provides current weather conditions for display in global stats
"""

import requests
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WEATHER_API_BASE = "https://api.weather.gov"
USER_AGENT = "FindTruckDriver/1.0 (contact@findtruckdriver.com)"
CACHE_DURATION_MINUTES = 30  # Longer cache for current conditions


@dataclass
class WeatherConditions:
    """Current weather conditions"""
    temperature_f: int  # Fahrenheit
    temperature_c: int  # Celsius
    condition: str  # "Clear", "Cloudy", "Rain", etc.
    emoji: str  # Weather emoji
    city: str  # City name
    state: str  # State abbreviation
    feels_like_f: Optional[int] = None
    wind_speed_mph: Optional[int] = None
    humidity_percent: Optional[int] = None


# Simple in-memory cache
_conditions_cache = {}


def get_current_conditions(latitude: float, longitude: float) -> Optional[WeatherConditions]:
    """
    Get current weather conditions for a location.

    Uses National Weather Service API (free, no API key required).
    Results are cached for 30 minutes.

    Args:
        latitude: Location latitude
        longitude: Location longitude

    Returns:
        WeatherConditions object, or None if unavailable
    """
    # Check cache first
    cache_key = f"{latitude:.4f},{longitude:.4f}"
    if cache_key in _conditions_cache:
        cached_time, cached_conditions = _conditions_cache[cache_key]
        if datetime.utcnow() - cached_time < timedelta(minutes=CACHE_DURATION_MINUTES):
            logger.debug(f"Weather conditions cache hit for {cache_key}")
            return cached_conditions

    try:
        # Step 1: Get grid point for location
        point_url = f"{WEATHER_API_BASE}/points/{latitude:.4f},{longitude:.4f}"
        logger.debug(f"Fetching weather grid point: {point_url}")

        point_response = requests.get(
            point_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5
        )

        if point_response.status_code != 200:
            logger.warning(
                f"Weather API point lookup failed: {point_response.status_code} "
                f"for {latitude}, {longitude}"
            )
            return None

        point_data = point_response.json()
        properties = point_data.get("properties", {})

        # Extract observation station URL
        observation_stations_url = properties.get("observationStations")
        if not observation_stations_url:
            logger.warning("No observation stations in weather API response")
            return None

        # Get city and state from the point data
        relative_location = properties.get("relativeLocation", {}).get("properties", {})
        raw_city = relative_location.get("city", "Unknown")
        state = relative_location.get("state", "")

        # Map small towns to their major metro area for better recognition
        # This helps users recognize where they are (e.g., "Fresno" vs "Biola")
        city = map_to_major_city(raw_city, state, latitude, longitude)

        # Step 2: Get nearest observation station
        stations_response = requests.get(
            observation_stations_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5
        )

        if stations_response.status_code != 200:
            logger.warning(f"Weather API stations lookup failed: {stations_response.status_code}")
            return None

        stations_data = stations_response.json()
        features = stations_data.get("features", [])

        if not features:
            logger.warning("No observation stations found")
            return None

        # Get the first (nearest) station
        station_url = features[0].get("id")

        # Step 3: Get latest observation
        observation_url = f"{station_url}/observations/latest"
        logger.debug(f"Fetching weather observation: {observation_url}")

        observation_response = requests.get(
            observation_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5
        )

        if observation_response.status_code != 200:
            logger.warning(f"Weather API observation lookup failed: {observation_response.status_code}")
            return None

        observation_data = observation_response.json()
        obs_props = observation_data.get("properties", {})

        # Extract temperature (Celsius)
        temp_c_raw = obs_props.get("temperature", {}).get("value")
        if temp_c_raw is None:
            logger.warning("No temperature data in observation")
            return None

        temp_c = int(temp_c_raw)
        temp_f = int((temp_c * 9/5) + 32)

        # Extract condition description
        condition_text = obs_props.get("textDescription", "Clear")

        # Extract additional data
        feels_like_c = obs_props.get("heatIndex", {}).get("value") or obs_props.get("windChill", {}).get("value")
        feels_like_f = int((feels_like_c * 9/5) + 32) if feels_like_c else None

        wind_speed_ms = obs_props.get("windSpeed", {}).get("value")
        wind_speed_mph = int(wind_speed_ms * 2.237) if wind_speed_ms else None

        humidity = obs_props.get("relativeHumidity", {}).get("value")
        humidity_percent = int(humidity) if humidity else None

        # Determine if night time based on icon URL
        # NWS icons: https://api.weather.gov/icons/.../night/few?size=medium
        icon_url = obs_props.get("icon", "")
        is_night = "/night/" in icon_url or "nt_" in icon_url

        # Map condition to emoji
        emoji = get_condition_emoji(condition_text, is_night)

        # Normalize city to nearest metro area
        display_city = get_metro_name(latitude, longitude, city)

        conditions = WeatherConditions(
            temperature_f=temp_f,
            temperature_c=temp_c,
            condition=condition_text,
            emoji=emoji,
            city=display_city,
            state=state,
            feels_like_f=feels_like_f,
            wind_speed_mph=wind_speed_mph,
            humidity_percent=humidity_percent
        )

        # Cache the results
        _conditions_cache[cache_key] = (datetime.utcnow(), conditions)

        logger.info(
            f"Current conditions: {display_city}, {state} - {temp_f}°F {condition_text} {emoji}"
        )

        return conditions

    except requests.Timeout:
        logger.warning(f"Weather API timeout for {latitude}, {longitude}")
        return None
    except requests.RequestException as e:
        logger.error(f"Weather API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Weather API error: {e}", exc_info=True)
        return None


# Metro Areas Configuration (Lat, Lon, Name)
# Using roughly 30 mile radius
METRO_AREAS = [
    (36.7378, -119.7871, "Fresno"),       # Fresno, CA
    (34.0522, -118.2437, "Los Angeles"),  # LA, CA
    (37.7749, -122.4194, "San Francisco"),# SF, CA
    (32.7157, -117.1611, "San Diego"),    # San Diego, CA
    (38.5816, -121.4944, "Sacramento"),   # Sacramento, CA
    (29.7604, -95.3698,  "Houston"),      # Houston, TX
    (32.7767, -96.7970,  "Dallas"),       # Dallas, TX
    (30.2672, -97.7431,  "Austin"),       # Austin, TX
    (29.4241, -98.4936,  "San Antonio"),  # San Antonio, TX
    (41.8781, -87.6298,  "Chicago"),      # Chicago, IL
    (40.7128, -74.0060,  "New York"),     # NYC, NY
    (25.7617, -80.1918,  "Miami"),        # Miami, FL
    (33.7490, -84.3880,  "Atlanta"),      # Atlanta, GA
    (39.7392, -104.9903, "Denver"),       # Denver, CO
    (36.1699, -115.1398, "Las Vegas"),    # Las Vegas, NV
    (33.4484, -112.0740, "Phoenix"),      # Phoenix, AZ
    (47.6062, -122.3321, "Seattle"),      # Seattle, WA
    (45.5152, -122.6784, "Portland"),     # Portland, OR
]


def get_metro_name(lat: float, lon: float, original_city: str) -> str:
    """
    Get major metro area name if within 30 miles, otherwise return original city.
    
    Args:
        lat: Latitude
        lon: Longitude
        original_city: Original city name from NWS
        
    Returns:
        Metro name or original city
    """
    import math

    def haversine_miles(lat1, lon1, lat2, lon2):
        R = 3958.8  # Earth radius in miles
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) * math.sin(dlon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    for m_lat, m_lon, m_name in METRO_AREAS:
        distance = haversine_miles(lat, lon, m_lat, m_lon)
        if distance <= 30:  # 30 mile radius
            return m_name
            
    return original_city


def map_to_major_city(city: str, state: str, latitude: float, longitude: float) -> str:
    """
    Map small towns to their major metro area for better user recognition.

    Args:
        city: City name from NWS
        state: State abbreviation
        latitude: Location latitude
        longitude: Location longitude

    Returns:
        Major city name if recognized, otherwise original city
    """
    # Define major metro areas with their approximate centers and radius
    # Format: (major_city, center_lat, center_lng, radius_miles)
    METRO_AREAS = {
        "CA": [
            ("Fresno", 36.7378, -119.7871, 30),
            ("Los Angeles", 34.0522, -118.2437, 50),
            ("San Francisco", 37.7749, -122.4194, 40),
            ("San Diego", 32.7157, -117.1611, 30),
            ("Sacramento", 38.5816, -121.4944, 30),
            ("San Jose", 37.3382, -121.8863, 25),
            ("Bakersfield", 35.3733, -119.0187, 25),
            ("Stockton", 37.9577, -121.2908, 20),
            ("Modesto", 37.6391, -120.9969, 20),
        ],
        "TX": [
            ("Houston", 29.7604, -95.3698, 50),
            ("Dallas", 32.7767, -96.7970, 50),
            ("San Antonio", 29.4241, -98.4936, 40),
            ("Austin", 30.2672, -97.7431, 35),
        ],
        "WY": [
            ("Cheyenne", 41.1400, -104.8202, 30),
        ],
        # Add more as needed
    }

    # Skip if state not in our metro areas
    if state not in METRO_AREAS:
        return city

    # Check if location is within any metro area
    for major_city, center_lat, center_lng, radius in METRO_AREAS[state]:
        from app.utils.location import calculate_distance
        distance = calculate_distance(latitude, longitude, center_lat, center_lng)

        if distance <= radius:
            logger.debug(f"Mapped {city} to {major_city} (distance: {distance:.1f} mi)")
            return major_city

    # Not in any metro area - return original
    return city


def get_condition_emoji(condition: str, is_night: bool = False) -> str:
    """
    Get appropriate emoji for weather condition.

    Args:
        condition: Weather condition text (e.g., "Partly Cloudy")
        is_night: Whether it is currently night time

    Returns:
        Emoji string representing the condition
    """
    condition_lower = condition.lower()

    # Time-independent conditions (severe stuff usually same day/night or has no good night variant)
    if "tornado" in condition_lower:
        return "🌪️"
    elif "thunder" in condition_lower or "t-storm" in condition_lower:
        return "⛈️"
    elif "snow" in condition_lower or "flurr" in condition_lower:
        return "❄️"
    elif "sleet" in condition_lower or "freezing" in condition_lower or "ice" in condition_lower:
        return "🧊"
    elif "rain" in condition_lower or "shower" in condition_lower or "drizzle" in condition_lower:
        return "🌧️"
    elif "fog" in condition_lower or "mist" in condition_lower or "haze" in condition_lower:
        return "🌫️"
    elif "wind" in condition_lower:
        return "💨"

    # Time-dependent conditions
    elif "cloud" in condition_lower or "overcast" in condition_lower:
        if "partly" in condition_lower or "few" in condition_lower or "scatter" in condition_lower:
            return "☁️" if is_night else "⛅"
        else:
            return "☁️"
    elif "clear" in condition_lower or "fair" in condition_lower or "sunny" in condition_lower:
        return "🌙" if is_night else "☀️"
    else:
        return "🌙" if is_night else "🌤️"  # Default fallback


def format_conditions_for_stats(conditions: WeatherConditions) -> str:
    """
    Format weather conditions for display in global stats.

    Args:
        conditions: WeatherConditions object

    Returns:
        Formatted string like "Fresno, CA: 72°F Clear ☀️"
    """
    return f"{conditions.city}, {conditions.state}: {conditions.temperature_f}°F {conditions.condition} {conditions.emoji}"


def format_conditions_detailed(conditions: WeatherConditions) -> Dict:
    """
    Format weather conditions as detailed dictionary for API response.

    Args:
        conditions: WeatherConditions object

    Returns:
        Dictionary with detailed weather info
    """
    result = {
        "temperature_f": conditions.temperature_f,
        "temperature_c": conditions.temperature_c,
        "condition": conditions.condition,
        "emoji": conditions.emoji,
        "location": f"{conditions.city}, {conditions.state}",
        "city": conditions.city,
        "state": conditions.state
    }

    if conditions.feels_like_f:
        result["feels_like_f"] = conditions.feels_like_f

    if conditions.wind_speed_mph:
        result["wind_speed_mph"] = conditions.wind_speed_mph

    if conditions.humidity_percent:
        result["humidity_percent"] = conditions.humidity_percent

    return result
