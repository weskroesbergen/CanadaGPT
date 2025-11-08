#!/bin/bash
# Setup script for PostgreSQL and historical data import

set -e

echo "========================================================"
echo "PostgreSQL Setup for Historical Data Import"
echo "========================================================"
echo

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "📦 Installing PostgreSQL 14..."
    brew install postgresql@14

    # Add to PATH
    echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
    export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
else
    echo "✅ PostgreSQL already installed"
    psql --version
fi

echo
echo "🚀 Starting PostgreSQL service..."
brew services start postgresql@14

# Wait for PostgreSQL to start
echo "⏳ Waiting for PostgreSQL to start..."
sleep 3

# Check if running
if pg_isready -q; then
    echo "✅ PostgreSQL is running"
else
    echo "⚠️  PostgreSQL may not be fully started yet. Waiting 5 more seconds..."
    sleep 5
    if pg_isready -q; then
        echo "✅ PostgreSQL is now running"
    else
        echo "❌ PostgreSQL failed to start. Try manually: brew services restart postgresql@14"
        exit 1
    fi
fi

echo
echo "🗄️  Creating openparliament_temp database..."
if psql -lqt | cut -d \| -f 1 | grep -qw openparliament_temp; then
    echo "⚠️  Database openparliament_temp already exists"
    read -p "Drop and recreate? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        dropdb openparliament_temp
        createdb openparliament_temp
        echo "✅ Database recreated"
    fi
else
    createdb openparliament_temp
    echo "✅ Database created: openparliament_temp"
fi

echo
echo "🐍 Installing Python dependencies..."
/Users/matthewdufresne/FedMCP/venv/bin/pip install psycopg2-binary requests

echo
echo "========================================================"
echo "✅ PostgreSQL Setup Complete!"
echo "========================================================"
echo
echo "Connection string: postgresql://localhost:5432/openparliament_temp"
echo
echo "Next steps:"
echo "1. Download Lipad data (optional):"
echo "   Visit: https://www.lipad.ca/data/"
echo "   Download CSV or XML package"
echo
echo "2. Run historical import:"
echo "   python test_complete_historical_import.py"
echo
echo "Estimated time:"
echo "  - OpenParliament only: ~1 hour"
echo "  - OpenParliament + Lipad: ~2 hours"
echo
