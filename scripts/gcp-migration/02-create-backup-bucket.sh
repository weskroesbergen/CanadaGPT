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
echo "Creating GCS Bucket for Neo4j Backups"
echo "========================================"
echo ""
echo "Project: $GCP_PROJECT_ID"
echo "Bucket: $BACKUP_BUCKET"
echo "Region: $GCP_REGION"
echo ""

# Check if bucket already exists
if gsutil ls -b gs://$BACKUP_BUCKET &> /dev/null; then
    echo "✅ Bucket already exists: gs://$BACKUP_BUCKET"
else
    # Create bucket
    echo "📦 Creating bucket..."
    gsutil mb -p $GCP_PROJECT_ID -c STANDARD -l $GCP_REGION gs://$BACKUP_BUCKET
    echo "✅ Bucket created"
fi

# Enable versioning
echo "🔄 Enabling versioning..."
gsutil versioning set on gs://$BACKUP_BUCKET
echo "✅ Versioning enabled"

# Set lifecycle policy for automatic cleanup
echo "🗑️  Setting lifecycle policy (delete backups after $BACKUP_RETENTION_DAYS days)..."
cat > /tmp/lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": $BACKUP_RETENTION_DAYS,
          "matchesPrefix": ["backups/"]
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "numNewerVersions": 3,
          "matchesPrefix": ["backups/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://$BACKUP_BUCKET
rm /tmp/lifecycle.json
echo "✅ Lifecycle policy set"

# Set bucket permissions
echo "🔒 Configuring bucket permissions..."
gsutil iam ch allUsers:objectViewer gs://$BACKUP_BUCKET || true
echo "✅ Bucket configured"

echo ""
echo "========================================"
echo "✅ Backup Bucket Ready!"
echo "========================================"
echo ""
echo "Bucket details:"
gsutil ls -L -b gs://$BACKUP_BUCKET | grep -E "(Location|Storage class|Versioning|Time created)"
echo ""
echo "Next step: Run ./scripts/gcp-migration/03-export-database.sh"
