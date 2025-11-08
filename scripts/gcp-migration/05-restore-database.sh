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
echo "Restoring Database to GCE VM"
echo "========================================"
echo ""

# Find the latest dump file in GCS
echo "1️⃣  Finding latest database dump..."
LATEST_DUMP=$(gsutil ls "gs://$BACKUP_BUCKET/migration/*.dump.gz" | tail -1)

if [ -z "$LATEST_DUMP" ]; then
    echo "❌ Error: No dump file found in gs://$BACKUP_BUCKET/migration/"
    echo "Please run ./scripts/gcp-migration/03-export-database.sh first"
    exit 1
fi

echo "✅ Found: $LATEST_DUMP"

# Create restore script
cat > /tmp/restore-neo4j.sh << 'RESTORE_SCRIPT'
#!/bin/bash
set -e

DUMP_FILE=$1
BUCKET=$2

echo "Downloading dump file from GCS..."
gsutil cp "$DUMP_FILE" /tmp/neo4j.dump.gz

echo "Decompressing dump file..."
gunzip /tmp/neo4j.dump.gz

echo "Stopping Neo4j..."
sudo systemctl stop neo4j

echo "Removing old database..."
sudo rm -rf /var/lib/neo4j/data/databases/neo4j
sudo rm -rf /var/lib/neo4j/data/transactions/neo4j

echo "Restoring database from dump..."
sudo neo4j-admin database load neo4j --from-path=/tmp --overwrite-destination=true

echo "Setting permissions..."
sudo chown -R neo4j:neo4j /var/lib/neo4j/data

echo "Starting Neo4j..."
sudo systemctl start neo4j

echo "Waiting for Neo4j to be ready..."
sleep 10

# Wait for Neo4j to accept connections
for i in {1..30}; do
    if sudo systemctl is-active --quiet neo4j; then
        echo "Neo4j is running!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Cleanup
rm -f /tmp/neo4j.dump
echo "Restore complete!"
RESTORE_SCRIPT

chmod +x /tmp/restore-neo4j.sh

echo ""
echo "2️⃣  Uploading restore script to VM..."
gcloud compute scp /tmp/restore-neo4j.sh $VM_NAME:/tmp/restore-neo4j.sh --zone=$GCP_ZONE

echo ""
echo "3️⃣  Running restore on VM..."
echo "   This may take 5-10 minutes for large databases..."
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command="bash /tmp/restore-neo4j.sh '$LATEST_DUMP' '$BACKUP_BUCKET'"

echo ""
echo "4️⃣  Verifying database..."
# Query database to get statistics
STATS=$(gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command="
    cypher-shell -u neo4j -p canadagpt2024 \"
    CALL apoc.meta.stats() YIELD nodeCount, relCount, labels, relTypes
    RETURN nodeCount, relCount, size(labels) as labelCount, size(relTypes) as relTypeCount
    \" --format plain
" 2>/dev/null | tail -1)

if [ -n "$STATS" ]; then
    echo "✅ Database verification:"
    echo "$STATS"
else
    echo "⚠️  Could not verify database stats"
    echo "   You can verify manually by connecting to Neo4j"
fi

# Cleanup
rm /tmp/restore-neo4j.sh

echo ""
echo "========================================"
echo "✅ Database Restored Successfully!"
echo "========================================"
echo ""
echo "Connection details:"
echo "  Bolt URI: bolt://$NEO4J_VM_INTERNAL_IP:7687"
echo "  Username: neo4j"
echo "  Password: canadagpt2024"
echo "  Browser: http://$NEO4J_VM_EXTERNAL_IP:7474"
echo ""
echo "Next step: Run ./scripts/gcp-migration/06-setup-backups.sh"
