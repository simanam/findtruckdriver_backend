"""
CB Handle Generator
Generates unique, trucker-themed anonymous display names for the map.
CB Handles are like CB radio handles - fun, anonymous identifiers.

Examples: "MidnightHauler_42", "DieselDrifter_77", "ChromeKnight_13"
"""

import random
from typing import Set, List, Optional

# Trucker-themed adjectives
ADJECTIVES = [
    "Midnight", "Chrome", "Diesel", "Thunder", "Iron",
    "Steel", "Dusty", "Lone", "Silver", "Golden",
    "Rusty", "Wild", "Blazing", "Rolling", "Mighty",
    "Asphalt", "Highway", "Rumbling", "Turbo", "Heavy",
    "Double", "Big", "Outlaw", "Freeway", "Nitro",
    "Road", "Black", "Red", "Blue", "Neon",
    "Gravel", "Mountain", "Prairie", "Desert", "Smoky",
    "Phantom", "Shadow", "Dark", "Bright", "Swift",
]

# Trucker-themed nouns
NOUNS = [
    "Hauler", "Drifter", "Knight", "Rider", "Ranger",
    "Runner", "Roller", "Cruiser", "Trucker", "Driver",
    "Bandit", "Maverick", "Phantom", "Wolf", "Eagle",
    "Hawk", "Bear", "Bull", "Mustang", "Stallion",
    "Hammer", "Wrench", "Gear", "Piston", "Axle",
    "Shifter", "Clutch", "Brake", "Throttle", "Diesel",
    "Rig", "Convoy", "Express", "Freight", "Cargo",
    "Tanker", "Flatbed", "Sleeper", "Cabover", "Peterbilt",
]

# Pattern: Adjective + Noun + Number
# This gives us 40 * 40 * 99 = 158,400 unique combinations


def generate_cb_handle(existing_handles: Optional[Set[str]] = None, max_attempts: int = 50) -> str:
    """
    Generate a unique CB handle.

    Args:
        existing_handles: Set of handles already in use (to avoid collisions)
        max_attempts: Maximum generation attempts before adding extra randomness

    Returns:
        A unique CB handle string like "MidnightHauler_42"
    """
    if existing_handles is None:
        existing_handles = set()

    for attempt in range(max_attempts):
        adjective = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        number = random.randint(1, 99)

        handle = f"{adjective}{noun}_{number}"

        if handle not in existing_handles:
            return handle

    # Fallback: use longer number for guaranteed uniqueness
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    number = random.randint(100, 9999)
    return f"{adjective}{noun}_{number}"


def generate_cb_handle_suggestions(
    count: int = 5,
    existing_handles: Optional[Set[str]] = None
) -> List[str]:
    """
    Generate multiple unique CB handle suggestions for the user to pick from.

    Args:
        count: Number of suggestions to generate
        existing_handles: Set of handles already in use

    Returns:
        List of unique CB handle suggestions
    """
    if existing_handles is None:
        existing_handles = set()

    suggestions = []
    local_used = set(existing_handles)

    for _ in range(count):
        handle = generate_cb_handle(local_used)
        suggestions.append(handle)
        local_used.add(handle)

    return suggestions


def is_valid_cb_handle(handle: str) -> bool:
    """
    Validate a user-provided CB handle.

    Rules:
    - 3-50 characters
    - Alphanumeric, underscores, hyphens only
    - Must start with a letter

    Args:
        handle: The CB handle to validate

    Returns:
        True if valid, False otherwise
    """
    if not handle or len(handle) < 3 or len(handle) > 50:
        return False

    if not handle[0].isalpha():
        return False

    if not all(c.isalnum() or c in ('_', '-') for c in handle):
        return False

    return True
