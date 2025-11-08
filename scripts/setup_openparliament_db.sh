#!/usr/bin/env bash
# Setup script for loading OpenParliament PostgreSQL dump into local database

set -e  # Exit on error

echo "========================================================================"
echo "OpenParliament Database Setup"
echo "========================================================================"

# Configuration
POSTGRES_BIN="/opt/homebrew/opt/postgresql@14/bin"
POSTGRES_DATA="/opt/homebrew/var/postgresql@14"
DB_NAME="openparliament"
DB_USER="fedmcp"
DUMP_FILE="$HOME/FedMCP/openparliament.public.sql.bz2"

# Check if dump file exists
if [ ! -f "$DUMP_FILE" ]; then
    echo "ERROR: Dump file not found at $DUMP_FILE"
    exit 1
fi

echo "1. Starting PostgreSQL..."
brew services start postgresql@14
sleep 3  # Give it time to start

echo "2. Checking PostgreSQL status..."
$POSTGRES_BIN/pg_isready || { echo "PostgreSQL failed to start"; exit 1; }

echo "3. Creating database and user..."
$POSTGRES_BIN/createdb $DB_NAME 2>/dev/null || echo "Database $DB_NAME already exists"
$POSTGRES_BIN/psql -d postgres << SQL
CREATE USER $DB_USER WITH PASSWORD 'fedmcp2024';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
SQL

echo "4. Loading OpenParliament dump (this will take 15-30 minutes)..."
echo "   Decompressing and loading $DUMP_FILE..."
bzcat "$DUMP_FILE" | $POSTGRES_BIN/psql -d $DB_NAME -U $DB_USER

echo "5. Verifying data load..."
$POSTGRES_BIN/psql -d $DB_NAME -U $DB_USER << SQL
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    (SELECT count(*) FROM pg_catalog.pg_class WHERE relname = tablename) AS row_estimate
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
SQL

echo "========================================================================"
echo "✅ OpenParliament database setup complete!"
echo "========================================================================"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: fedmcp2024"
echo "Host: localhost"
echo "Port: 5432"
echo ""
echo "Connection string: postgresql://$DB_USER:fedmcp2024@localhost:5432/$DB_NAME"
echo ""
echo "Next steps:"
echo "1. Add PostgreSQL credentials to packages/data-pipeline/.env"
echo "2. Run: canadagpt-ingest --openparliament"
