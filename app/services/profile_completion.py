"""
Profile Completion Calculator
3-tier weighted calculation for profile completion percentage.
Also handles badge awarding logic.
"""

# Tier 1: Essential (60% weight) - 6 fields
TIER_1_FIELDS = ["years_experience", "haul_type", "equipment_type", "cdl_class", "cdl_state", "bio"]
TIER_1_WEIGHT = 0.6

# Tier 2: Professional (25% weight) - 4 fields
TIER_2_FIELDS = ["company_name", "endorsements", "specialties", "looking_for"]
TIER_2_WEIGHT = 0.25

# Tier 3: Verification (15% weight) - 3 fields
TIER_3_FIELDS = ["mc_number", "dot_number", "preferred_haul"]
TIER_3_WEIGHT = 0.15


def _field_filled(profile: dict, field: str) -> bool:
    """Check if a profile field has a meaningful value."""
    val = profile.get(field)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if isinstance(val, list) and len(val) == 0:
        return False
    return True


def calculate_completion(profile: dict) -> int:
    """
    Calculate profile completion percentage using 3-tier weighted system.

    Tier 1 (Essential - 60%): years_experience, haul_type, equipment_type, cdl_class, cdl_state, bio
    Tier 2 (Professional - 25%): company_name, endorsements, specialties, looking_for
    Tier 3 (Verification - 15%): mc_number, dot_number, preferred_haul

    Args:
        profile: Dictionary of profile field values.

    Returns:
        Completion percentage as integer (0-100).
    """
    if not profile:
        return 0

    tier1_count = sum(1 for f in TIER_1_FIELDS if _field_filled(profile, f))
    tier2_count = sum(1 for f in TIER_2_FIELDS if _field_filled(profile, f))
    tier3_count = sum(1 for f in TIER_3_FIELDS if _field_filled(profile, f))

    tier1_pct = (tier1_count / len(TIER_1_FIELDS)) * TIER_1_WEIGHT
    tier2_pct = (tier2_count / len(TIER_2_FIELDS)) * TIER_2_WEIGHT
    tier3_pct = (tier3_count / len(TIER_3_FIELDS)) * TIER_3_WEIGHT

    total = tier1_pct + tier2_pct + tier3_pct
    return min(round(total * 100), 100)


def check_badges(profile: dict, existing_badges: list = None) -> list:
    """
    Check and award badges based on profile data.

    Badge categories:
    - Completion badges: profile_starter (25%), halfway_there (50%), almost_complete (75%), profile_complete (100%)
    - Experience badges: one_year_veteran (1yr), five_year_veteran (5yr), decade_driver (10yr), road_legend (20yr)
    - Miles badges: million_miler (1M+ miles)
    - Status badges: open_to_work

    Args:
        profile: Dictionary of profile field values.
        existing_badges: List of already-awarded badge dicts.

    Returns:
        Updated list of badge dicts (existing + newly awarded).
    """
    if existing_badges is None:
        existing_badges = []

    badge_ids = {b.get("id") for b in existing_badges}
    new_badges = list(existing_badges)

    completion = calculate_completion(profile)

    # Completion badges
    if completion >= 25 and "profile_starter" not in badge_ids:
        new_badges.append({"id": "profile_starter", "name": "Profile Starter", "awarded_at": None})

    if completion >= 50 and "halfway_there" not in badge_ids:
        new_badges.append({"id": "halfway_there", "name": "Halfway There", "awarded_at": None})

    if completion >= 75 and "almost_complete" not in badge_ids:
        new_badges.append({"id": "almost_complete", "name": "Almost Complete", "awarded_at": None})

    if completion >= 100 and "profile_complete" not in badge_ids:
        new_badges.append({"id": "profile_complete", "name": "Profile Complete", "awarded_at": None})

    # Experience badges
    years = profile.get("years_experience", 0) or 0
    if years >= 1 and "one_year_veteran" not in badge_ids:
        new_badges.append({"id": "one_year_veteran", "name": "1 Year Veteran", "awarded_at": None})
    if years >= 5 and "five_year_veteran" not in badge_ids:
        new_badges.append({"id": "five_year_veteran", "name": "5 Year Veteran", "awarded_at": None})
    if years >= 10 and "decade_driver" not in badge_ids:
        new_badges.append({"id": "decade_driver", "name": "Decade Driver", "awarded_at": None})
    if years >= 20 and "road_legend" not in badge_ids:
        new_badges.append({"id": "road_legend", "name": "Road Legend", "awarded_at": None})

    # Million miler
    miles = profile.get("estimated_miles", 0) or 0
    if miles >= 1_000_000 and "million_miler" not in badge_ids:
        new_badges.append({"id": "million_miler", "name": "Million Miler", "awarded_at": None})

    # Open to work
    if profile.get("open_to_work") and "open_to_work" not in badge_ids:
        new_badges.append({"id": "open_to_work", "name": "Open to Work", "awarded_at": None})

    # Verification badges (from role_details)
    role_details = profile.get("role_details", {})
    if isinstance(role_details, str):
        import json
        try:
            role_details = json.loads(role_details)
        except (json.JSONDecodeError, TypeError):
            role_details = {}

    if role_details.get("fmcsa_verified") and "fmcsa_verified" not in badge_ids:
        new_badges.append({"id": "fmcsa_verified", "name": "FMCSA Verified", "awarded_at": None})

    if role_details.get("google_verified") and "google_verified" not in badge_ids:
        new_badges.append({"id": "google_verified", "name": "Google Verified", "awarded_at": None})

    return new_badges
