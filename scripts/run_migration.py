"""
Apply SQL migration to Supabase using direct SQL execution
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY")

db = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def run_migration(migration_file: str):
    """Apply a SQL migration"""

    logger.info(f"Reading migration: {migration_file}")

    with open(migration_file, 'r') as f:
        sql = f.read()

    logger.info("Executing migration SQL...")

    try:
        # Split by semicolons to execute statement by statement
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        for i, statement in enumerate(statements, 1):
            # Skip comments and empty lines
            if not statement or statement.startswith('--'):
                continue

            logger.info(f"Executing statement {i}/{len(statements)}...")

            # Use rpc to execute raw SQL
            try:
                result = db.rpc('exec_sql', {'query': statement}).execute()
                logger.info(f"✓ Statement {i} executed successfully")
            except Exception as e:
                # Try using postgrest directly
                logger.warning(f"RPC failed, trying direct execution: {e}")
                # Note: Supabase Python client doesn't support raw SQL directly
                # We need to execute via SQL editor or use psycopg2
                raise Exception("Cannot execute raw SQL through Supabase client. Please use Supabase SQL Editor.")

        logger.info("✅ Migration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.info("\nPlease apply the migration manually:")
        logger.info("1. Go to: https://supabase.com/dashboard/project/_/sql")
        logger.info(f"2. Copy contents of: {migration_file}")
        logger.info("3. Paste and execute in SQL editor")
        sys.exit(1)

if __name__ == "__main__":
    migration_file = "migrations/005_add_osm_query_cache.sql"

    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)

    logger.info("="*80)
    logger.info("MIGRATION RUNNER")
    logger.info("="*80)

    run_migration(migration_file)
