"""
Test Weather Integration
Tests the weather API service and follow-up question integration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.weather_api import (
    get_weather_alerts,
    has_severe_alerts,
    get_most_severe_alert,
    get_alert_emoji,
    should_warn_driver
)
from app.services.follow_up_engine import FollowUpEngine


def test_weather_api():
    """Test weather API with known locations"""

    print("=" * 60)
    print("Testing Weather API Integration")
    print("=" * 60)

    # Test locations (areas that often have weather alerts)
    test_locations = [
        (41.3114, -105.5911, "Cheyenne, WY (often has winter weather)"),
        (35.5951, -82.5515, "Asheville, NC (mountain weather)"),
        (29.7604, -95.3698, "Houston, TX (tropical storms)"),
        (47.6062, -122.3321, "Seattle, WA (rain/wind)"),
        (36.7783, -119.4179, "Fresno, CA (fog/heat)"),
    ]

    for lat, lng, name in test_locations:
        print(f"\n{name}")
        print(f"Location: ({lat}, {lng})")
        print("-" * 60)

        try:
            alerts = get_weather_alerts(lat, lng)

            if not alerts:
                print("✓ No active weather alerts")
                continue

            print(f"✓ Found {len(alerts)} active alert(s):")

            for i, alert in enumerate(alerts, 1):
                print(f"\n  Alert {i}:")
                print(f"  Event: {alert.event}")
                print(f"  Severity: {alert.severity}")
                print(f"  Urgency: {alert.urgency}")
                print(f"  Emoji: {get_alert_emoji(alert.event)}")
                print(f"  Headline: {alert.headline[:100]}...")

            # Test severity check
            if has_severe_alerts(alerts):
                print("\n  ⚠️  SEVERE/EXTREME ALERT DETECTED")

            # Test most severe
            most_severe = get_most_severe_alert(alerts)
            if most_severe:
                print(f"\n  Most Severe: {most_severe.event}")

            # Test driver warning logic
            for status in ["rolling", "parked", "waiting"]:
                if should_warn_driver(alerts, status):
                    print(f"  → Should warn {status.upper()} drivers")

        except Exception as e:
            print(f"✗ Error: {e}")


def test_follow_up_integration():
    """Test weather integration with follow-up engine"""

    print("\n" + "=" * 60)
    print("Testing Follow-Up Engine Integration")
    print("=" * 60)

    from app.models.follow_up import StatusContext

    # Simulate weather scenario
    print("\nScenario: Driver goes ROLLING during winter storm")
    print("-" * 60)

    engine = FollowUpEngine()

    # Create context (no previous status)
    context = StatusContext()

    # Location with potential winter weather
    latitude, longitude = 41.3114, -105.5911  # Cheyenne, WY

    question = engine.get_follow_up_question(
        new_status="rolling",
        context=context,
        facility_name=None,
        latitude=latitude,
        longitude=longitude
    )

    if question:
        print("\n✓ Follow-up question generated:")
        print(f"  Type: {question.question_type}")
        print(f"  Text: {question.text}")
        if question.subtext:
            print(f"  Subtext: {question.subtext}")
        print(f"  Options: {[opt.label for opt in question.options]}")
        print(f"  Skippable: {question.skippable}")
        if question.auto_dismiss_seconds:
            print(f"  Auto-dismiss: {question.auto_dismiss_seconds}s")
    else:
        print("\n✓ No weather alerts - normal question flow")


def test_weather_caching():
    """Test that weather results are cached"""

    print("\n" + "=" * 60)
    print("Testing Weather Caching")
    print("=" * 60)

    import time

    lat, lng = 35.5951, -82.5515

    # First call
    print("\nFirst call (should hit API)...")
    start = time.time()
    alerts1 = get_weather_alerts(lat, lng)
    time1 = time.time() - start
    print(f"✓ Took {time1:.3f}s, found {len(alerts1)} alerts")

    # Second call (should use cache)
    print("\nSecond call (should use cache)...")
    start = time.time()
    alerts2 = get_weather_alerts(lat, lng)
    time2 = time.time() - start
    print(f"✓ Took {time2:.3f}s, found {len(alerts2)} alerts")

    if time2 < time1 * 0.1:  # Should be 10x faster
        print("\n✓ Caching working correctly!")
    else:
        print("\n⚠️  Caching may not be working (times too similar)")


if __name__ == "__main__":
    print("\n")
    print("🌤️  Weather Integration Test Suite")
    print("=" * 60)

    try:
        # Test weather API
        test_weather_api()

        # Test follow-up integration
        test_follow_up_integration()

        # Test caching
        test_weather_caching()

        print("\n" + "=" * 60)
        print("✅ All tests complete!")
        print("=" * 60)
        print("\nNote: Weather alerts vary by location and time.")
        print("If no alerts found, try different locations or times.")
        print("\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
