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
echo "Configuring Firewall Rules"
echo "========================================"
echo ""

# Create firewall rule for Neo4j Bolt (internal only)
echo "1️⃣  Creating firewall rule for Neo4j Bolt (7687)..."
if gcloud compute firewall-rules describe allow-neo4j-bolt &> /dev/null; then
    echo "   Rule already exists, updating..."
    gcloud compute firewall-rules update allow-neo4j-bolt \
        --allow=tcp:7687 \
        --source-ranges=10.0.0.0/8 \
        --target-tags=neo4j \
        --description="Allow Neo4j Bolt connections from internal network"
else
    gcloud compute firewall-rules create allow-neo4j-bolt \
        --allow=tcp:7687 \
        --source-ranges=10.0.0.0/8 \
        --target-tags=neo4j \
        --description="Allow Neo4j Bolt connections from internal network"
fi
echo "✅ Bolt firewall rule configured"

# Create firewall rule for Neo4j Browser (HTTP - temporary for setup)
echo ""
echo "2️⃣  Creating firewall rule for Neo4j Browser (7474)..."
echo "   ⚠️  This allows access from your IP only for initial setup"
MY_IP=$(curl -s https://api.ipify.org)
echo "   Your IP: $MY_IP"

if gcloud compute firewall-rules describe allow-neo4j-browser &> /dev/null; then
    echo "   Rule already exists, updating..."
    gcloud compute firewall-rules update allow-neo4j-browser \
        --allow=tcp:7474 \
        --source-ranges=$MY_IP/32 \
        --target-tags=neo4j \
        --description="Allow Neo4j Browser from specific IP (temporary)"
else
    gcloud compute firewall-rules create allow-neo4j-browser \
        --allow=tcp:7474 \
        --source-ranges=$MY_IP/32 \
        --target-tags=neo4j \
        --description="Allow Neo4j Browser from specific IP (temporary)"
fi
echo "✅ Browser firewall rule configured"

# Create firewall rule for SSH
echo ""
echo "3️⃣  Creating firewall rule for SSH (22)..."
if gcloud compute firewall-rules describe allow-ssh-neo4j &> /dev/null; then
    echo "   Rule already exists"
else
    gcloud compute firewall-rules create allow-ssh-neo4j \
        --allow=tcp:22 \
        --source-ranges=$MY_IP/32 \
        --target-tags=neo4j \
        --description="Allow SSH from specific IP"
fi
echo "✅ SSH firewall rule configured"

echo ""
echo "4️⃣  Listing active firewall rules for Neo4j..."
gcloud compute firewall-rules list --filter="targetTags:neo4j" --format="table(name,allowed,sourceRanges,targetTags)"

echo ""
echo "========================================"
echo "✅ Firewall Rules Configured!"
echo "========================================"
echo ""
echo "Active rules:"
echo "  - Bolt (7687): Internal network only (10.0.0.0/8)"
echo "  - Browser (7474): Your IP only ($MY_IP)"
echo "  - SSH (22): Your IP only ($MY_IP)"
echo ""
echo "⚠️  SECURITY RECOMMENDATIONS:"
echo "1. After testing, remove the browser rule:"
echo "   gcloud compute firewall-rules delete allow-neo4j-browser"
echo ""
echo "2. For production, use a VPN or Cloud IAP for SSH access"
echo ""
echo "3. Consider using Private Google Access for GCS backups"
echo ""
echo "Next step: Run ./scripts/gcp-migration/08-update-app-config.sh"
