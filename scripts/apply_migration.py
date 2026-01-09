"""
Apply SQL migration to Supabase database
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def apply_migration(migration_file: str):
    """Apply a SQL migration file"""

    logger.info(f"Applying migration: {migration_file}")

    with open(migration_file, 'r') as f:
        sql = f.read()

    try:
        # Execute SQL using Supabase RPC (if available) or direct query
        # Note: Supabase Python client doesn't have direct SQL execution
        # This would typically be done through Supabase Dashboard SQL Editor
        # or using psycopg2 directly

        logger.warning("This script shows the SQL to apply.")
        logger.warning("Please copy and paste into Supabase SQL Editor:")
        logger.warning("https://supabase.com/dashboard/project/_/sql")
        print("\n" + "="*80)
        print(sql)
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <migration_file>")
        print("Example: python apply_migration.py ../migrations/005_add_osm_query_cache.sql")
        sys.exit(1)

    migration_file = sys.argv[1]

    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)

    apply_migration(migration_file)
