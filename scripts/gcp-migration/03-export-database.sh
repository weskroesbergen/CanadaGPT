#!/bin/bash
set -e

# Load configuration
if [ ! -f scripts/gcp-migration/.env ]; then
    echo "❌ Error: Configuration file not found"
    echo "Please run ./scripts/gcp-migration/01-setup-gcp.sh first"
    exit 1
fi

source scripts/gcp-migration/.env

echo "========================================"
echo "Exporting Neo4j Database"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if Neo4j container exists
if ! docker ps -a --format '{{.Names}}' | grep -q 'canadagpt-neo4j'; then
    echo "❌ Error: Neo4j container not found"
    echo "Make sure Docker Compose is set up correctly"
    exit 1
fi

echo "⚠️  WARNING: This will stop your local Neo4j database!"
echo "The export process requires Neo4j to be stopped."
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Export cancelled"
    exit 1
fi

# Create backup directory
mkdir -p backups
BACKUP_FILE="backups/neo4j-export-$(date +%Y%m%d-%H%M%S).dump"

echo ""
echo "1️⃣  Stopping Neo4j container..."
docker-compose stop neo4j
echo "✅ Neo4j stopped"

echo ""
echo "2️⃣  Creating database dump..."
echo "   This may take several minutes for large databases..."

docker run --rm \
  -v canadagpt_neo4j_data:/data \
  -v $(pwd)/backups:/backup \
  neo4j:5.14-community \
  neo4j-admin database dump neo4j \
  --to-path=/backup \
  --verbose

# Find the dump file
DUMP_FILE=$(ls -t backups/*.dump 2>/dev/null | head -1)

if [ -z "$DUMP_FILE" ]; then
    echo "❌ Error: Dump file not created"
    echo "Starting Neo4j container..."
    docker-compose start neo4j
    exit 1
fi

echo "✅ Database dumped to: $DUMP_FILE"

# Get file size
FILE_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "   File size: $FILE_SIZE"

echo ""
echo "3️⃣  Compressing dump file..."
gzip -f "$DUMP_FILE"
COMPRESSED_FILE="${DUMP_FILE}.gz"
COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo "✅ Compressed to: $COMPRESSED_FILE ($COMPRESSED_SIZE)"

echo ""
echo "4️⃣  Uploading to Google Cloud Storage..."
gsutil cp "$COMPRESSED_FILE" "gs://$BACKUP_BUCKET/migration/$(basename $COMPRESSED_FILE)"
echo "✅ Uploaded to: gs://$BACKUP_BUCKET/migration/$(basename $COMPRESSED_FILE)"

echo ""
echo "5️⃣  Restarting local Neo4j container..."
docker-compose start neo4j

# Wait for Neo4j to be ready
echo "   Waiting for Neo4j to start..."
sleep 5

if docker ps | grep -q canadagpt-neo4j; then
    echo "✅ Neo4j restarted successfully"
else
    echo "⚠️  Warning: Neo4j may not have started properly"
    echo "   Check with: docker-compose logs neo4j"
fi

echo ""
echo "========================================"
echo "✅ Export Complete!"
echo "========================================"
echo ""
echo "Export details:"
echo "  Local file: $COMPRESSED_FILE"
echo "  GCS location: gs://$BACKUP_BUCKET/migration/$(basename $COMPRESSED_FILE)"
echo "  Compressed size: $COMPRESSED_SIZE"
echo ""
echo "Next step: Run ./scripts/gcp-migration/04-create-vm.sh"
