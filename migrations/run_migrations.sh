#!/bin/bash

# Database Migration Runner
# Applies SQL migrations to Supabase database

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Database Migration Runner${NC}"
echo "================================="

# Load environment variables
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
elif [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL not set in .env${NC}"
    exit 1
fi

# Get migration directory
MIGRATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}Migration directory: ${MIGRATION_DIR}${NC}"
echo -e "${YELLOW}Database: ${DATABASE_URL%%\?*}${NC}"  # Hide password
echo ""

# Function to check if psql is available
check_psql() {
    if ! command -v psql &> /dev/null; then
        echo -e "${RED}Error: psql not found. Please install PostgreSQL client.${NC}"
        echo "  macOS: brew install postgresql"
        echo "  Ubuntu: sudo apt-get install postgresql-client"
        exit 1
    fi
}

# Function to check if migration was already applied
is_migration_applied() {
    local migration_name=$1
    psql "$DATABASE_URL" -t -c "SELECT EXISTS(SELECT 1 FROM migration_history WHERE migration_name='$migration_name');" 2>/dev/null | grep -q 't'
}

# Function to apply a migration
apply_migration() {
    local migration_file=$1
    local migration_name=$(basename "$migration_file" .sql)

    echo -e "${YELLOW}Checking: ${migration_name}${NC}"

    # Check if migration was already applied
    if is_migration_applied "$migration_name"; then
        echo -e "${GREEN}  ✓ Already applied${NC}"
        return 0
    fi

    echo -e "${YELLOW}  → Applying migration...${NC}"

    # Apply migration
    if psql "$DATABASE_URL" -f "$migration_file" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Successfully applied${NC}"
    else
        echo -e "${RED}  ✗ Failed to apply migration${NC}"
        echo -e "${RED}    File: ${migration_file}${NC}"
        # Show actual error
        psql "$DATABASE_URL" -f "$migration_file"
        exit 1
    fi
}

# Main execution
main() {
    check_psql

    echo -e "${YELLOW}Finding migration files...${NC}"

    # Get all .sql files in order
    migration_files=$(ls -1 "$MIGRATION_DIR"/*.sql 2>/dev/null | grep -E '[0-9]{3}_.*\.sql' | sort)

    if [ -z "$migration_files" ]; then
        echo -e "${YELLOW}No migration files found.${NC}"
        exit 0
    fi

    echo -e "${GREEN}Found $(echo "$migration_files" | wc -l | tr -d ' ') migration files${NC}"
    echo ""

    # Apply each migration
    while IFS= read -r migration_file; do
        apply_migration "$migration_file"
    done <<< "$migration_files"

    echo ""
    echo -e "${GREEN}✓ All migrations completed successfully!${NC}"

    # Show migration history
    echo ""
    echo -e "${YELLOW}Migration History:${NC}"
    psql "$DATABASE_URL" -c "SELECT migration_name, applied_at FROM migration_history ORDER BY applied_at DESC LIMIT 5;"
}

# Handle force flag
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    echo -e "${YELLOW}⚠️  Force mode enabled - will reapply all migrations${NC}"
    echo -e "${YELLOW}Clearing migration history...${NC}"
    psql "$DATABASE_URL" -c "TRUNCATE TABLE migration_history;" 2>/dev/null || true
fi

# Run main
main

echo ""
echo -e "${GREEN}Done!${NC}"
