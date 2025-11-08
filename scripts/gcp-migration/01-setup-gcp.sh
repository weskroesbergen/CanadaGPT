#!/bin/bash
set -e

echo "=================================="
echo "Neo4j GCP Migration - Setup Script"
echo "=================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ gcloud CLI found"
echo ""

# Authenticate if not already authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "🔐 Authenticating with Google Cloud..."
    gcloud auth login
    echo ""
fi

# Set or prompt for project ID
echo "📋 GCP Project Setup"
echo ""
read -p "Enter your GCP Project ID (or press Enter to create new): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo ""
    read -p "Enter a project ID for your new project (e.g., canadagpt-prod): " PROJECT_ID
    echo "Creating new project: $PROJECT_ID"
    gcloud projects create $PROJECT_ID --name="CanadaGPT Production"
    echo "✅ Project created"
    echo ""
    echo "⚠️  IMPORTANT: Enable billing for this project in the GCP Console:"
    echo "   https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    echo ""
    read -p "Press Enter after enabling billing..."
fi

# Set the project
gcloud config set project $PROJECT_ID
echo "✅ Using project: $PROJECT_ID"
echo ""

# Enable required APIs
echo "🔧 Enabling required GCP APIs..."
gcloud services enable compute.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    cloudresourcemanager.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com

echo "✅ APIs enabled"
echo ""

# Set default region and zone
echo "🌍 Setting default region and zone..."
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
echo "✅ Region set to us-central1"
echo ""

# Save configuration
cat > scripts/gcp-migration/.env << EOF
# GCP Configuration
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=us-central1
GCP_ZONE=us-central1-a

# Neo4j Configuration
NEO4J_VERSION=5.14
NEO4J_PASSWORD=canadagpt2024

# VM Configuration
VM_NAME=canadagpt-neo4j
VM_MACHINE_TYPE=n2-standard-2
VM_DISK_SIZE=50GB

# Backup Configuration
BACKUP_BUCKET=${PROJECT_ID}-neo4j-backups
BACKUP_RETENTION_DAYS=30
EOF

echo "✅ Configuration saved to scripts/gcp-migration/.env"
echo ""
echo "=================================="
echo "✅ GCP Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Run: ./scripts/gcp-migration/02-create-backup-bucket.sh"
echo "2. Then: ./scripts/gcp-migration/03-export-database.sh"
