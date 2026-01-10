"""
Weather API Service
Integrates with National Weather Service API for real-time weather alerts
"""

import requests
import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

WEATHER_API_BASE = "https://api.weather.gov"
USER_AGENT = "FindTruckDriver/1.0 (contact@findtruckdriver.com)"
CACHE_DURATION_MINUTES = 15


@dataclass
class WeatherAlert:
    """Weather alert from NWS"""
    event: str  # e.g., "Winter Storm Warning"
    severity: str  # "Extreme", "Severe", "Moderate", "Minor"
    urgency: str  # "Immediate", "Expected", "Future"
    certainty: str  # "Observed", "Likely", "Possible"
    headline: str
    description: str
    instruction: Optional[str]
    onset: Optional[str]  # ISO timestamp when alert starts
    expires: Optional[str]  # ISO timestamp when alert expires


# Simple in-memory cache (in production, use Redis)
_weather_cache = {}


def get_weather_alerts(latitude: float, longitude: float) -> List[WeatherAlert]:
    """
    Get active weather alerts for a location.

    Uses National Weather Service API (free, no API key required).
    Results are cached for 15 minutes to reduce API calls.

    Args:
        latitude: Location latitude
        longitude: Location longitude

    Returns:
        List of active weather alerts
    """
    # Check cache first
    cache_key = f"{latitude:.4f},{longitude:.4f}"
    if cache_key in _weather_cache:
        cached_time, cached_alerts = _weather_cache[cache_key]
        if datetime.utcnow() - cached_time < timedelta(minutes=CACHE_DURATION_MINUTES):
            logger.debug(f"Weather alerts cache hit for {cache_key}")
            return cached_alerts

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
            return []

        point_data = point_response.json()

        # Extract forecast zone URL
        zone_url = point_data.get("properties", {}).get("forecastZone")
        if not zone_url:
            logger.warning("No forecast zone in weather API response")
            return []

        # Get zone ID from URL (e.g., "WYZ106" from ".../zones/forecast/WYZ106")
        zone_id = zone_url.split("/")[-1]

        # Step 2: Get active alerts for zone
        alerts_url = f"{WEATHER_API_BASE}/alerts/active/zone/{zone_id}"
        logger.debug(f"Fetching weather alerts: {alerts_url}")

        alerts_response = requests.get(
            alerts_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5
        )

        if alerts_response.status_code != 200:
            logger.warning(f"Weather API alerts lookup failed: {alerts_response.status_code}")
            return []

        alerts_data = alerts_response.json()

        # Parse alerts
        alerts = []
        for feature in alerts_data.get("features", []):
            props = feature.get("properties", {})

            alerts.append(WeatherAlert(
                event=props.get("event", "Weather Alert"),
                severity=props.get("severity", "Unknown"),
                urgency=props.get("urgency", "Unknown"),
                certainty=props.get("certainty", "Unknown"),
                headline=props.get("headline", ""),
                description=props.get("description", ""),
                instruction=props.get("instruction"),
                onset=props.get("onset"),
                expires=props.get("expires")
            ))

        logger.info(f"Found {len(alerts)} weather alerts for zone {zone_id}")

        # Cache the results
        _weather_cache[cache_key] = (datetime.utcnow(), alerts)

        return alerts

    except requests.Timeout:
        logger.warning(f"Weather API timeout for {latitude}, {longitude}")
        return []
    except requests.RequestException as e:
        logger.error(f"Weather API request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Weather API error: {e}", exc_info=True)
        return []


def has_severe_alerts(alerts: List[WeatherAlert]) -> bool:
    """
    Check if any alerts are severe or extreme.

    Args:
        alerts: List of weather alerts

    Returns:
        True if any alert is Severe or Extreme severity
    """
    return any(
        alert.severity in ["Severe", "Extreme"]
        for alert in alerts
    )


def has_immediate_alerts(alerts: List[WeatherAlert]) -> bool:
    """
    Check if any alerts require immediate action.

    Args:
        alerts: List of weather alerts

    Returns:
        True if any alert has Immediate urgency
    """
    return any(
        alert.urgency == "Immediate"
        for alert in alerts
    )


def get_most_severe_alert(alerts: List[WeatherAlert]) -> Optional[WeatherAlert]:
    """
    Get the most severe alert from a list.

    Prioritizes by:
    1. Severity (Extreme > Severe > Moderate > Minor)
    2. Urgency (Immediate > Expected > Future)

    Args:
        alerts: List of weather alerts

    Returns:
        The most severe alert, or None if list is empty
    """
    if not alerts:
        return None

    severity_order = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}
    urgency_order = {"Immediate": 3, "Expected": 2, "Future": 1, "Unknown": 0}

    return max(
        alerts,
        key=lambda a: (
            severity_order.get(a.severity, 0),
            urgency_order.get(a.urgency, 0)
        )
    )


def get_alert_emoji(event: str) -> str:
    """
    Get appropriate emoji for weather event.

    Args:
        event: Weather event name (e.g., "Winter Storm Warning")

    Returns:
        Emoji string representing the weather event
    """
    event_lower = event.lower()

    if "tornado" in event_lower:
        return "🌪️"
    elif "thunder" in event_lower or "lightning" in event_lower:
        return "⛈️"
    elif "snow" in event_lower or "blizzard" in event_lower:
        return "❄️"
    elif "ice" in event_lower or "freezing" in event_lower:
        return "🧊"
    elif "flood" in event_lower:
        return "🌊"
    elif "wind" in event_lower:
        return "💨"
    elif "heat" in event_lower:
        return "🔥"
    elif "fog" in event_lower:
        return "🌫️"
    elif "rain" in event_lower:
        return "🌧️"
    elif "hurricane" in event_lower:
        return "🌀"
    else:
        return "⚠️"


def should_warn_driver(alerts: List[WeatherAlert], driver_status: str) -> bool:
    """
    Determine if driver should be warned about weather.

    Args:
        alerts: List of weather alerts
        driver_status: Current driver status ("rolling", "parked", "waiting")

    Returns:
        True if driver should be warned
    """
    if not alerts:
        return False

    # Always warn for severe/extreme alerts
    if has_severe_alerts(alerts):
        return True

    # Warn rolling drivers about immediate alerts
    if driver_status == "rolling" and has_immediate_alerts(alerts):
        return True

    return False


def get_weather_summary(alerts: List[WeatherAlert]) -> Optional[str]:
    """
    Get a brief summary of weather conditions.

    Args:
        alerts: List of weather alerts

    Returns:
        Brief summary string, or None if no alerts
    """
    if not alerts:
        return None

    most_severe = get_most_severe_alert(alerts)
    if not most_severe:
        return None

    emoji = get_alert_emoji(most_severe.event)
    return f"{emoji} {most_severe.event}"
