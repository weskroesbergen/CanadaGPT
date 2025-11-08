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
echo "Tagging GCP Resources as Production"
echo "========================================"
echo ""
echo "Project: $GCP_PROJECT_ID"
echo ""

# Get project number (needed for tagging)
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)")
echo "Project Number: $PROJECT_NUMBER"

# Check if Resource Manager API is enabled
echo ""
echo "1️⃣  Enabling Resource Manager Tags API..."
gcloud services enable cloudresourcemanager.googleapis.com --project=$GCP_PROJECT_ID
echo "✅ API enabled"

# Create tag key for environment (if it doesn't exist)
echo ""
echo "2️⃣  Creating 'environment' tag key..."

TAG_KEY_ID="environment"
TAG_KEY_NAME="tagKeys/${TAG_KEY_ID}"

# Try to create the tag key
if gcloud resource-manager tags keys create $TAG_KEY_ID \
    --parent=projects/$GCP_PROJECT_ID \
    --purpose=GCE_FIREWALL \
    --purpose-data=network=projects/$GCP_PROJECT_ID/global/networks/default \
    --description="Environment tag for resource categorization" 2>/dev/null; then
    echo "✅ Tag key 'environment' created"
else
    echo "ℹ️  Tag key 'environment' already exists or using different approach"

    # Alternative: Create without purpose if the above fails
    if gcloud resource-manager tags keys create $TAG_KEY_ID \
        --parent=projects/$GCP_PROJECT_ID \
        --description="Environment tag for resource categorization" 2>/dev/null; then
        echo "✅ Tag key 'environment' created"
    else
        echo "ℹ️  Tag key 'environment' already exists, continuing..."
    fi
fi

# Get the full tag key name
TAG_KEY_FULL=$(gcloud resource-manager tags keys list \
    --parent=projects/$GCP_PROJECT_ID \
    --filter="shortName:environment" \
    --format="value(name)" | head -1)

if [ -z "$TAG_KEY_FULL" ]; then
    echo "❌ Error: Could not find or create tag key 'environment'"
    echo ""
    echo "You may need to create it manually in the GCP Console:"
    echo "https://console.cloud.google.com/iam-admin/tags?project=$GCP_PROJECT_ID"
    exit 1
fi

echo "   Full tag key: $TAG_KEY_FULL"

# Create tag value 'production' under the environment key
echo ""
echo "3️⃣  Creating 'production' tag value..."

if gcloud resource-manager tags values create production \
    --parent=$TAG_KEY_FULL \
    --description="Production environment" 2>/dev/null; then
    echo "✅ Tag value 'production' created"
else
    echo "ℹ️  Tag value 'production' already exists, continuing..."
fi

# Get the full tag value name
TAG_VALUE_FULL=$(gcloud resource-manager tags values list \
    --parent=$TAG_KEY_FULL \
    --filter="shortName:production" \
    --format="value(name)" | head -1)

if [ -z "$TAG_VALUE_FULL" ]; then
    echo "❌ Error: Could not find or create tag value 'production'"
    exit 1
fi

echo "   Full tag value: $TAG_VALUE_FULL"

# Tag the project
echo ""
echo "4️⃣  Tagging project as production..."

PROJECT_RESOURCE="//cloudresourcemanager.googleapis.com/projects/$PROJECT_NUMBER"

if gcloud resource-manager tags bindings create \
    --tag-value=$TAG_VALUE_FULL \
    --parent=$PROJECT_RESOURCE \
    --location=global 2>/dev/null; then
    echo "✅ Project tagged as production"
else
    echo "ℹ️  Project may already be tagged, updating..."
    # Note: Tags are immutable once created, so this may fail if already exists
fi

# Tag the Neo4j VM
echo ""
echo "5️⃣  Tagging Neo4j VM as production..."

if [ -n "$VM_NAME" ]; then
    VM_RESOURCE="//compute.googleapis.com/projects/$GCP_PROJECT_ID/zones/$GCP_ZONE/instances/$VM_NAME"

    if gcloud resource-manager tags bindings create \
        --tag-value=$TAG_VALUE_FULL \
        --parent=$VM_RESOURCE \
        --location=$GCP_ZONE 2>/dev/null; then
        echo "✅ VM tagged as production"
    else
        echo "ℹ️  VM may already be tagged"
    fi
else
    echo "⚠️  VM not created yet, skipping VM tagging"
fi

# List all tags for verification
echo ""
echo "6️⃣  Listing all resource tags..."
echo ""
echo "Tag Keys:"
gcloud resource-manager tags keys list --parent=projects/$GCP_PROJECT_ID

echo ""
echo "Tag Values for 'environment':"
gcloud resource-manager tags values list --parent=$TAG_KEY_FULL

echo ""
echo "Tag Bindings on Project:"
gcloud resource-manager tags bindings list \
    --parent=$PROJECT_RESOURCE \
    --location=global 2>/dev/null || echo "No bindings found or not yet propagated"

echo ""
echo "========================================"
echo "✅ Production Tagging Complete!"
echo "========================================"
echo ""
echo "Tagged resources:"
echo "  - Project: $GCP_PROJECT_ID"
if [ -n "$VM_NAME" ]; then
echo "  - VM: $VM_NAME"
fi
echo ""
echo "Tag details:"
echo "  Key: environment"
echo "  Value: production"
echo ""
echo "You can view tags in the GCP Console:"
echo "https://console.cloud.google.com/iam-admin/tags?project=$GCP_PROJECT_ID"
echo ""
echo "To use tags in billing reports, enable tag-based billing:"
echo "https://console.cloud.google.com/billing"
