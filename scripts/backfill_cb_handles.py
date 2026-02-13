"""
Backfill CB Handles for existing drivers.
Run once after migration 008.
Usage: python -m scripts.backfill_cb_handles
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_admin
from app.services.cb_handle_generator import generate_cb_handle


def backfill():
    db = get_db_admin()

    # Get all drivers without cb_handle
    response = db.from_("drivers").select("id, handle").is_("cb_handle", "null").execute()

    if not response.data:
        print("No drivers need backfill.")
        return

    # Get existing handles to avoid conflicts
    existing = db.from_("drivers").select("cb_handle").not_.is_("cb_handle", "null").execute()
    existing_handles = {d["cb_handle"] for d in existing.data} if existing.data else set()

    count = 0
    for driver in response.data:
        handle = generate_cb_handle(existing_handles)
        existing_handles.add(handle)

        db.from_("drivers").update({"cb_handle": handle}).eq("id", driver["id"]).execute()
        count += 1
        print(f"  {driver['handle']} -> {handle}")

    print(f"\nBackfilled {count} drivers with CB handles.")


if __name__ == "__main__":
    backfill()
