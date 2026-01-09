"""
Apply SQL migration using psycopg2 (direct PostgreSQL connection)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL environment variable")

def run_migration(migration_file: str):
    """Apply a SQL migration using psycopg2"""

    logger.info(f"Reading migration: {migration_file}")

    with open(migration_file, 'r') as f:
        sql = f.read()

    logger.info("Connecting to database...")

    try:
        import psycopg2

        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False  # Use transaction

        cur = conn.cursor()

        logger.info("Executing migration SQL...")

        try:
            # Execute the entire SQL file
            cur.execute(sql)
            conn.commit()

            logger.info("✅ Migration completed successfully!")

            # Check what was created
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('osm_query_cache', 'facilities')
                ORDER BY table_name
            """)

            tables = cur.fetchall()
            logger.info(f"Tables verified: {[t[0] for t in tables]}")

            # Check new columns on facilities
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'facilities'
                AND column_name IN ('data_source', 'osm_id', 'osm_version', 'last_verified_at')
                ORDER BY column_name
            """)

            columns = cur.fetchall()
            logger.info(f"New columns on facilities: {[c[0] for c in columns]}")

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise

        finally:
            cur.close()
            conn.close()

    except ImportError:
        logger.error("❌ psycopg2 not installed")
        logger.info("Install with: pip install psycopg2-binary")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
    else:
        migration_file = "migrations/005_add_osm_query_cache.sql"

    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)

    logger.info("="*80)
    logger.info("POSTGRESQL MIGRATION RUNNER")
    logger.info("="*80)
    logger.info(f"Database: {DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'unknown'}")
    logger.info(f"Migration: {migration_file}")
    logger.info("="*80)

    response = input("\nProceed with migration? (y/n): ")
    if response.lower() != 'y':
        logger.info("Migration cancelled")
        sys.exit(0)

    run_migration(migration_file)
