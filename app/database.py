"""
Database Connection
Supabase client setup and database connection management
"""

from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""

    def __init__(self):
        self._client: Client | None = None
        self._admin_client: Client | None = None

    def get_client(self) -> Client:
        """
        Get Supabase client for regular operations (uses public key).
        This client respects Row Level Security.
        """
        if self._client is None:
            logger.info("Initializing Supabase client...")

            public_key = settings.supabase_public_key

            if not public_key:
                raise ValueError(
                    "Supabase public key not found. Please set either:\n"
                    "  - SUPABASE_PUBLISHABLE_KEY (new format)\n"
                    "  - SUPABASE_ANON_KEY (legacy format)\n"
                    "Check your .env file and Supabase Dashboard → Project Settings → API"
                )

            self._client = create_client(settings.supabase_url, public_key)
            logger.info("✅ Supabase client initialized")
        return self._client

    def get_admin_client(self) -> Client:
        """
        Get Supabase admin client (uses private key).
        This client BYPASSES Row Level Security.
        Use for admin operations, stats aggregation, system tasks.
        """
        if self._admin_client is None:
            logger.info("Initializing Supabase admin client...")

            private_key = settings.supabase_private_key

            if not private_key:
                raise ValueError(
                    "Supabase private key not found. Please set either:\n"
                    "  - SUPABASE_SECRET_KEY (new format)\n"
                    "  - SUPABASE_SERVICE_KEY (legacy format)\n"
                    "Check your .env file and Supabase Dashboard → Project Settings → API\n"
                    "⚠️  NEVER expose the private key in frontend code!"
                )

            self._admin_client = create_client(settings.supabase_url, private_key)
            logger.info("✅ Supabase admin client initialized")
        return self._admin_client

    def close(self):
        """Close database connections"""
        # Supabase Python client doesn't require explicit closing
        # But we can reset the instances
        self._client = None
        self._admin_client = None
        logger.info("Database connections closed")


# Global database instance
db = Database()


def get_db_client() -> Client:
    """
    Dependency function to get database client.
    Use this for operations that should respect RLS.
    """
    return db.get_client()


def get_db_admin() -> Client:
    """
    Dependency function to get admin database client.
    Use this for operations that need to bypass RLS.
    """
    return db.get_admin_client()


async def check_connection() -> bool:
    """
    Check if database connection is working.
    Returns True if connected, False otherwise.
    """
    try:
        client = db.get_admin_client()

        # Try a simple query
        response = client.from_("drivers").select("id").limit(1).execute()

        logger.info("✅ Database connection successful")
        return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def initialize_database():
    """
    Initialize database connections on startup.
    Call this in the FastAPI lifespan.
    """
    logger.info("Initializing database connections...")

    # Initialize both clients
    db.get_client()
    db.get_admin_client()

    # Test connection
    is_connected = await check_connection()

    if not is_connected:
        logger.warning("⚠️  Database connection check failed - continuing anyway")
    else:
        logger.info("✅ Database initialized successfully")


async def close_database():
    """
    Close database connections on shutdown.
    Call this in the FastAPI lifespan.
    """
    logger.info("Closing database connections...")
    db.close()
    logger.info("✅ Database connections closed")
