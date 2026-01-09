# Database Migrations

This directory contains SQL migration files for the Find a Truck Driver backend.

## Migration Strategy

We use **raw SQL migrations** instead of Alembic ORM migrations because:
- Supabase requires PostgreSQL-specific features (PostGIS, RLS policies)
- Raw SQL gives us full control over Supabase configuration
- Easier to version control and review changes

## Structure

```
migrations/
├── README.md           # This file
├── 001_initial_schema.sql    # Initial database setup
├── 002_add_driver_locations.sql  # Add location tracking
└── run_migrations.sh   # Script to apply migrations
```

## Running Migrations

### Development (Local)

Run migrations against your Supabase database:

```bash
# From finddriverbackend directory
./migrations/run_migrations.sh
```

### Production

Migrations are automatically applied during deployment:

```bash
# Apply all pending migrations
./migrations/run_migrations.sh production
```

## Creating New Migrations

1. **Create new SQL file** with incremental number:
   ```bash
   touch migrations/003_add_facilities_table.sql
   ```

2. **Write migration SQL**:
   ```sql
   -- Migration: 003_add_facilities_table
   -- Description: Add facilities table for truck stops
   -- Date: 2026-01-09

   CREATE TABLE IF NOT EXISTS facilities (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       name VARCHAR(255) NOT NULL,
       ...
   );
   ```

3. **Test locally first**:
   ```bash
   ./migrations/run_migrations.sh
   ```

4. **Commit to git**:
   ```bash
   git add migrations/003_add_facilities_table.sql
   git commit -m "Add facilities table migration"
   ```

## Migration Files

### 001_initial_schema.sql
- Creates `drivers` table
- Sets up RLS policies
- Creates indexes

### 002_add_driver_locations.sql
- Creates `driver_locations` table with PostGIS
- Creates `status_history` table
- Adds geospatial indexes
- Sets up RLS for location privacy

## Rollback

To rollback a migration, create a new migration that reverses the changes:

```sql
-- Migration: 004_rollback_facilities
-- Rolls back migration 003

DROP TABLE IF EXISTS facilities;
```

## Best Practices

1. **Never modify existing migrations** - create new ones instead
2. **Always use IF NOT EXISTS** for tables/indexes
3. **Test migrations on a copy of production data** before deploying
4. **Include RLS policies** in the same migration as the table
5. **Use transactions** where appropriate
6. **Document breaking changes** in migration comments

## Checking Migration Status

```bash
# List applied migrations
psql $DATABASE_URL -c "SELECT * FROM migration_history ORDER BY applied_at DESC;"
```

## Troubleshooting

### Migration fails on Supabase

1. Check Supabase logs in dashboard
2. Ensure PostGIS extension is enabled
3. Verify RLS policies don't conflict
4. Check for syntax errors with `\i migrations/XXX.sql` in psql

### Missing tables in production

Run migration script manually:
```bash
./migrations/run_migrations.sh production --force
```
