"""
Miles Calculator
Estimates total career miles based on years of experience and haul type.
Uses industry averages per ATA Trucking Association data.
"""

ANNUAL_MILES_BY_HAUL_TYPE = {
    "long_haul": 125000,
    "otr": 130000,
    "regional": 80000,
    "local": 50000,
    "dedicated": 100000,
}

DEFAULT_ANNUAL_MILES = 100000


def calculate_estimated_miles(years: int, haul_type: str = None) -> int:
    """
    Calculate estimated career miles based on years of experience and haul type.

    Args:
        years: Number of years of driving experience.
        haul_type: Type of haul (long_haul, otr, regional, local, dedicated).

    Returns:
        Estimated total career miles.
    """
    annual = ANNUAL_MILES_BY_HAUL_TYPE.get(haul_type, DEFAULT_ANNUAL_MILES) if haul_type else DEFAULT_ANNUAL_MILES
    return annual * max(years, 0)


def format_miles_display(miles: int) -> str:
    """
    Format miles into a human-readable display string.

    Args:
        miles: Total miles to format.

    Returns:
        Formatted string (e.g., "1.3M miles", "125K miles", "500 miles").
    """
    if miles >= 1_000_000:
        return f"{miles / 1_000_000:.1f}M miles"
    elif miles >= 1_000:
        return f"{miles / 1_000:.0f}K miles"
    return f"{miles} miles"
