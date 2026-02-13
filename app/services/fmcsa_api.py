"""
FMCSA API Service
Integrates with FMCSA QCMobile API for carrier/company lookups
"""

import requests
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

FMCSA_API_BASE = "https://mobile.fmcsa.dot.gov/qc/services"
CACHE_DURATION_MINUTES = 60


@dataclass
class FMCSACarrier:
    """Carrier information from FMCSA"""
    legal_name: str
    dba_name: Optional[str] = None
    dot_number: Optional[str] = None
    mc_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    power_units: Optional[int] = None
    drivers: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Simple in-memory cache
_fmcsa_cache: Dict[str, tuple] = {}


def _parse_carrier(content: dict) -> Optional[FMCSACarrier]:
    """Parse a carrier record from FMCSA API response."""
    try:
        carrier = content.get("carrier", {})
        if not carrier:
            return None

        # MC number is sometimes in docket numbers
        mc_number = None
        docket_numbers = content.get("docketNumbers", [])
        if isinstance(docket_numbers, list):
            for d in docket_numbers:
                prefix = d.get("prefix", "")
                number = d.get("docketNumber", "")
                if prefix == "MC" and number:
                    mc_number = f"MC-{number}"
                    break

        # Build address from parts
        address_parts = [
            carrier.get("phyStreet"),
        ]
        address = ", ".join(p for p in address_parts if p) or None

        # Parse power_units and drivers safely
        power_units = carrier.get("totalPowerUnits")
        drivers_count = carrier.get("totalDrivers")
        try:
            power_units = int(power_units) if power_units else None
        except (ValueError, TypeError):
            power_units = None
        try:
            drivers_count = int(drivers_count) if drivers_count else None
        except (ValueError, TypeError):
            drivers_count = None

        return FMCSACarrier(
            legal_name=carrier.get("legalName", "Unknown"),
            dba_name=carrier.get("dbaName") or None,
            dot_number=str(carrier.get("dotNumber", "")) or None,
            mc_number=mc_number,
            address=address,
            city=carrier.get("phyCity") or None,
            state=carrier.get("phyState") or None,
            zip_code=carrier.get("phyZipcode") or None,
            phone=carrier.get("telephone") or None,
            power_units=power_units,
            drivers=drivers_count,
        )
    except Exception as e:
        logger.warning(f"Failed to parse FMCSA carrier record: {e}")
        return None


def search_by_dot(dot_number: str, web_key: str) -> Optional[FMCSACarrier]:
    """
    Look up a carrier by DOT number.

    Args:
        dot_number: The USDOT number to search for
        web_key: FMCSA API WebKey

    Returns:
        FMCSACarrier or None if not found
    """
    cache_key = f"dot:{dot_number}"
    if cache_key in _fmcsa_cache:
        cached_time, cached_result = _fmcsa_cache[cache_key]
        if datetime.utcnow() - cached_time < timedelta(minutes=CACHE_DURATION_MINUTES):
            return cached_result

    try:
        url = f"{FMCSA_API_BASE}/carriers/{dot_number}"
        params = {"webKey": web_key}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            logger.warning(f"FMCSA API returned {response.status_code} for DOT {dot_number}")
            return None

        data = response.json()
        content = data.get("content", {})

        carrier = _parse_carrier(content)
        _fmcsa_cache[cache_key] = (datetime.utcnow(), carrier)
        return carrier

    except requests.Timeout:
        logger.warning(f"FMCSA API timeout for DOT {dot_number}")
        return None
    except requests.RequestException as e:
        logger.error(f"FMCSA API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"FMCSA API error: {e}", exc_info=True)
        return None


def search_by_name(name: str, web_key: str, limit: int = 10) -> List[FMCSACarrier]:
    """
    Search carriers by company name.

    Args:
        name: Company name to search for
        web_key: FMCSA API WebKey
        limit: Max results to return

    Returns:
        List of matching FMCSACarrier records
    """
    cache_key = f"name:{name.lower().strip()}:{limit}"
    if cache_key in _fmcsa_cache:
        cached_time, cached_result = _fmcsa_cache[cache_key]
        if datetime.utcnow() - cached_time < timedelta(minutes=CACHE_DURATION_MINUTES):
            return cached_result

    try:
        url = f"{FMCSA_API_BASE}/carriers/name/{name}"
        params = {"webKey": web_key, "size": min(limit, 25)}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            logger.warning(f"FMCSA API returned {response.status_code} for name '{name}'")
            return []

        data = response.json()
        content_list = data.get("content", [])

        if not isinstance(content_list, list):
            content_list = [content_list] if content_list else []

        carriers = []
        for item in content_list[:limit]:
            carrier = _parse_carrier(item)
            if carrier:
                carriers.append(carrier)

        _fmcsa_cache[cache_key] = (datetime.utcnow(), carriers)
        return carriers

    except requests.Timeout:
        logger.warning(f"FMCSA API timeout for name '{name}'")
        return []
    except requests.RequestException as e:
        logger.error(f"FMCSA API request error: {e}")
        return []
    except Exception as e:
        logger.error(f"FMCSA API error: {e}", exc_info=True)
        return []
