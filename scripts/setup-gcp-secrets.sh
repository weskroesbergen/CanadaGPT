#!/bin/bash

# ============================================
# GCP Secret Manager Setup for CanadaGPT
# ============================================
#
# This script creates and stores API keys and secrets in GCP Secret Manager
# for secure production deployment of the CanadaGPT application.
#
# Prerequisites:
# 1. gcloud CLI installed and authenticated
# 2. Appropriate IAM permissions to create secrets
# 3. Secret Manager API enabled in your GCP project
#
# Usage:
#   chmod +x scripts/setup-gcp-secrets.sh
#   ./scripts/setup-gcp-secrets.sh [PROJECT_ID]
#
# ============================================

set -e  # Exit on error

# Configuration
PROJECT_ID="${1:-canada-gpt-ca}"
REGION="us-central1"

# Service accounts that need access to secrets
GRAPH_API_SA="canadagpt-graph-api-sa@${PROJECT_ID}.iam.gserviceaccount.com"
FRONTEND_SA="canadagpt-frontend-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "🔐 GCP Secret Manager Setup for CanadaGPT"
echo "==========================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📋 Setting GCP project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"
echo ""

# Enable Secret Manager API
echo "🔧 Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com
echo "✅ Secret Manager API enabled"
echo ""

# Function to create or update a secret
create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3

    echo "🔑 Processing secret: $SECRET_NAME"

    # Check if secret exists
    if gcloud secrets describe "$SECRET_NAME" &> /dev/null; then
        echo "   Secret exists, adding new version..."
        echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
    else
        echo "   Creating new secret..."
        echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
            --data-file=- \
            --replication-policy="automatic" \
            --labels="app=canadagpt,component=security"
    fi

    echo "   ✅ $SECRET_NAME configured"
    echo ""
}

# Function to grant access to a secret
grant_secret_access() {
    local SECRET_NAME=$1
    local SERVICE_ACCOUNT=$2

    echo "🔓 Granting $SERVICE_ACCOUNT access to $SECRET_NAME..."
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
    echo "   ✅ Access granted"
    echo ""
}

# Check if user wants to generate new keys or use existing ones
echo "⚠️  IMPORTANT: This script will create/update secrets in GCP Secret Manager."
echo ""
read -p "Do you want to generate NEW API keys? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔐 Generating new API keys..."
    FRONTEND_API_KEY=$(openssl rand -hex 32)
    PUBLIC_API_KEY=$(openssl rand -hex 32)
    ADMIN_API_KEY=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -base64 32)
    AUTH_SECRET=$(openssl rand -base64 32)
    echo "✅ Keys generated"
    echo ""
else
    echo "📝 Please enter existing keys (or press Enter to skip):"
    echo ""
    read -p "FRONTEND_API_KEY: " FRONTEND_API_KEY
    read -p "PUBLIC_API_KEY: " PUBLIC_API_KEY
    read -p "ADMIN_API_KEY: " ADMIN_API_KEY
    read -p "JWT_SECRET: " JWT_SECRET
    read -p "AUTH_SECRET: " AUTH_SECRET
    echo ""
fi

# Create secrets in GCP
echo "📦 Creating/updating secrets in GCP Secret Manager..."
echo ""

if [ -n "$FRONTEND_API_KEY" ]; then
    create_or_update_secret "canadagpt-frontend-api-key" "$FRONTEND_API_KEY" "API key for CanadaGPT frontend application"
    grant_secret_access "canadagpt-frontend-api-key" "$GRAPH_API_SA"
fi

if [ -n "$PUBLIC_API_KEY" ]; then
    create_or_update_secret "canadagpt-public-api-key" "$PUBLIC_API_KEY" "Public read-only API key for CanadaGPT"
    grant_secret_access "canadagpt-public-api-key" "$GRAPH_API_SA"
fi

if [ -n "$ADMIN_API_KEY" ]; then
    create_or_update_secret "canadagpt-admin-api-key" "$ADMIN_API_KEY" "Admin API key for CanadaGPT management"
    grant_secret_access "canadagpt-admin-api-key" "$GRAPH_API_SA"
fi

if [ -n "$JWT_SECRET" ]; then
    create_or_update_secret "canadagpt-jwt-secret" "$JWT_SECRET" "JWT secret for Neo4jGraphQL authorization"
    grant_secret_access "canadagpt-jwt-secret" "$GRAPH_API_SA"
fi

if [ -n "$AUTH_SECRET" ]; then
    create_or_update_secret "canadagpt-auth-secret" "$AUTH_SECRET" "NextAuth AUTH_SECRET for session encryption"
    grant_secret_access "canadagpt-auth-secret" "$FRONTEND_SA"
fi

# Display summary
echo ""
echo "==========================================="
echo "✅ GCP Secret Manager Setup Complete!"
echo "==========================================="
echo ""
echo "📋 Secrets created:"
echo "   - canadagpt-frontend-api-key"
echo "   - canadagpt-public-api-key"
echo "   - canadagpt-admin-api-key"
echo "   - canadagpt-jwt-secret"
echo "   - canadagpt-auth-secret"
echo ""
echo "🔒 Permissions granted to:"
echo "   - $GRAPH_API_SA (API keys + JWT)"
echo "   - $FRONTEND_SA (AUTH_SECRET)"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Update deployment scripts to reference these secrets:"
echo "   - scripts/deploy-cloud-run.sh (graph-api)"
echo "   - scripts/deploy-frontend-cloudrun.sh (frontend)"
echo ""
echo "2. Deploy with secrets:"
echo "   cd /Users/matthewdufresne/CanadaGPT"
echo "   ./scripts/deploy-cloud-run.sh"
echo "   ./scripts/deploy-frontend-cloudrun.sh"
echo ""
echo "3. Verify secrets are accessible:"
echo "   gcloud secrets versions access latest --secret=canadagpt-frontend-api-key"
echo ""
echo "⚠️  SECURITY REMINDERS:"
echo "   - Never commit secrets to git"
echo "   - Rotate secrets regularly (every 90 days)"
echo "   - Monitor secret access logs in Cloud Console"
echo "   - Set up alerts for unauthorized access attempts"
echo ""
