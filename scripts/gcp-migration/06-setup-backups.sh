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
echo "Setting Up Automated Backups"
echo "========================================"
echo ""

# Create backup script for VM
cat > /tmp/neo4j-backup.sh << 'BACKUP_SCRIPT'
#!/bin/bash
set -e

# Configuration
BUCKET="${BACKUP_BUCKET}"
BACKUP_DIR="/var/backups/neo4j"
DATE=$(date +%Y%m%d-%H%M%S)
DUMP_FILE="$BACKUP_DIR/neo4j-backup-$DATE.dump"

echo "$(date): Starting Neo4j backup..." | tee -a /var/log/neo4j-backup.log

# Stop Neo4j
echo "Stopping Neo4j..." | tee -a /var/log/neo4j-backup.log
systemctl stop neo4j

# Create dump
echo "Creating database dump..." | tee -a /var/log/neo4j-backup.log
neo4j-admin database dump neo4j --to-path=$BACKUP_DIR

# Find the created dump file
LATEST_DUMP=$(ls -t $BACKUP_DIR/*.dump | head -1)

# Start Neo4j
echo "Starting Neo4j..." | tee -a /var/log/neo4j-backup.log
systemctl start neo4j

# Wait for Neo4j to be ready
for i in {1..30}; do
    if systemctl is-active --quiet neo4j; then
        echo "Neo4j restarted successfully" | tee -a /var/log/neo4j-backup.log
        break
    fi
    sleep 2
done

# Compress dump
echo "Compressing backup..." | tee -a /var/log/neo4j-backup.log
gzip -f "$LATEST_DUMP"
COMPRESSED_FILE="${LATEST_DUMP}.gz"

# Upload to GCS
echo "Uploading to GCS..." | tee -a /var/log/neo4j-backup.log
gsutil cp "$COMPRESSED_FILE" "gs://${BACKUP_BUCKET}/backups/$(basename $COMPRESSED_FILE)"

# Cleanup local backups older than 7 days
echo "Cleaning up old local backups..." | tee -a /var/log/neo4j-backup.log
find $BACKUP_DIR -name "*.dump.gz" -mtime +7 -delete

FILE_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo "$(date): Backup complete! Size: $FILE_SIZE" | tee -a /var/log/neo4j-backup.log
echo "Uploaded to: gs://${BACKUP_BUCKET}/backups/$(basename $COMPRESSED_FILE)" | tee -a /var/log/neo4j-backup.log

# Send success notification (optional - requires setup)
# gcloud logging write neo4j-backup "Backup completed successfully: $(basename $COMPRESSED_FILE)"
BACKUP_SCRIPT

# Replace placeholder with actual bucket name
sed -i "s/\${BACKUP_BUCKET}/$BACKUP_BUCKET/g" /tmp/neo4j-backup.sh

echo "1️⃣  Uploading backup script to VM..."
gcloud compute scp /tmp/neo4j-backup.sh $VM_NAME:/tmp/neo4j-backup.sh --zone=$GCP_ZONE

echo ""
echo "2️⃣  Installing backup script on VM..."
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command='
    sudo mv /tmp/neo4j-backup.sh /usr/local/bin/neo4j-backup.sh
    sudo chmod +x /usr/local/bin/neo4j-backup.sh
    sudo chown root:root /usr/local/bin/neo4j-backup.sh
'

echo ""
echo "3️⃣  Setting up cron job (daily at 2:00 AM)..."
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command='
    # Add cron job
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/neo4j-backup.sh") | crontab -
    echo "Cron job installed:"
    crontab -l | grep neo4j-backup
'

echo ""
echo "4️⃣  Testing backup script..."
echo "   Running test backup (this may take a few minutes)..."
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command='sudo /usr/local/bin/neo4j-backup.sh'

echo ""
echo "5️⃣  Verifying backup in GCS..."
gsutil ls -lh "gs://$BACKUP_BUCKET/backups/" | tail -5

# Cleanup
rm /tmp/neo4j-backup.sh

echo ""
echo "========================================"
echo "✅ Automated Backups Configured!"
echo "========================================"
echo ""
echo "Backup configuration:"
echo "  Schedule: Daily at 2:00 AM (server time)"
echo "  Location: gs://$BACKUP_BUCKET/backups/"
echo "  Retention: 30 days (GCS lifecycle policy)"
echo "  Local retention: 7 days"
echo ""
echo "Backup logs: /var/log/neo4j-backup.log (on VM)"
echo ""
echo "To manually trigger a backup:"
echo "  gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command='sudo /usr/local/bin/neo4j-backup.sh'"
echo ""
echo "Next step: Run ./scripts/gcp-migration/07-setup-firewall.sh"
