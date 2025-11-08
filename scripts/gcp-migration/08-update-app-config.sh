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
echo "Updating Application Configuration"
echo "========================================"
echo ""

# Check if VM IP is available
if [ -z "$NEO4J_VM_INTERNAL_IP" ]; then
    echo "Getting VM internal IP..."
    NEO4J_VM_INTERNAL_IP=$(gcloud compute instances describe $VM_NAME \
        --zone=$GCP_ZONE \
        --format="value(networkInterfaces[0].networkIP)")
    echo "NEO4J_VM_INTERNAL_IP=$NEO4J_VM_INTERNAL_IP" >> scripts/gcp-migration/.env
fi

echo "Neo4j VM Internal IP: $NEO4J_VM_INTERNAL_IP"
echo ""

# Backup existing .env file
if [ -f packages/graph-api/.env ]; then
    echo "1️⃣  Backing up existing .env file..."
    cp packages/graph-api/.env packages/graph-api/.env.backup.$(date +%Y%m%d-%H%M%S)
    echo "✅ Backup created"
fi

# Read existing .env file
if [ -f packages/graph-api/.env ]; then
    source packages/graph-api/.env
fi

# Update or create .env file
echo ""
echo "2️⃣  Updating GraphQL API configuration..."

cat > packages/graph-api/.env << EOF
# Neo4j Configuration (Cloud)
NEO4J_URI=bolt://${NEO4J_VM_INTERNAL_IP}:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=canadagpt2024

# Server Configuration
PORT=4000
NODE_ENV=development

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173

# GCP Configuration (for future use)
GCP_PROJECT_ID=$GCP_PROJECT_ID
GCP_REGION=$GCP_REGION

# Migration Note: Using GCE VM at ${NEO4J_VM_INTERNAL_IP}
# To revert to local: NEO4J_URI=bolt://localhost:7687
EOF

echo "✅ GraphQL API .env updated"

# Store password in Secret Manager (for production)
echo ""
echo "3️⃣  Storing Neo4j password in Secret Manager..."

if gcloud secrets describe neo4j-password --project=$GCP_PROJECT_ID &> /dev/null; then
    echo "   Secret already exists, updating..."
    echo -n "canadagpt2024" | gcloud secrets versions add neo4j-password --data-file=-
else
    echo -n "canadagpt2024" | gcloud secrets create neo4j-password \
        --data-file=- \
        --replication-policy=automatic
fi

echo "✅ Password stored in Secret Manager"

# Create a test script
echo ""
echo "4️⃣  Creating test connection script..."
cat > scripts/gcp-migration/test-connection.sh << 'TEST_SCRIPT'
#!/bin/bash
source scripts/gcp-migration/.env

echo "Testing Neo4j connection..."
echo "URI: bolt://${NEO4J_VM_INTERNAL_IP}:7687"
echo ""

# Test with cypher-shell (if installed locally)
if command -v cypher-shell &> /dev/null; then
    echo "Running query..."
    cypher-shell -a "bolt://${NEO4J_VM_INTERNAL_IP}:7687" \
        -u neo4j -p canadagpt2024 \
        "CALL apoc.meta.stats() YIELD nodeCount, relCount RETURN nodeCount, relCount"
else
    echo "cypher-shell not installed locally, testing via VM..."
    gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command="
        cypher-shell -u neo4j -p canadagpt2024 \
        'CALL apoc.meta.stats() YIELD nodeCount, relCount RETURN nodeCount, relCount'
    "
fi
TEST_SCRIPT

chmod +x scripts/gcp-migration/test-connection.sh

echo "✅ Test script created"

echo ""
echo "========================================"
echo "✅ Configuration Updated!"
echo "========================================"
echo ""
echo "Configuration changes:"
echo "  - packages/graph-api/.env updated"
echo "  - NEO4J_URI: bolt://${NEO4J_VM_INTERNAL_IP}:7687"
echo "  - Backup saved: packages/graph-api/.env.backup.*"
echo "  - Password stored in Secret Manager"
echo ""
echo "To test the connection:"
echo "  ./scripts/gcp-migration/test-connection.sh"
echo ""
echo "To start GraphQL API with cloud Neo4j:"
echo "  cd packages/graph-api && pnpm dev"
echo ""
echo "To revert to local Neo4j:"
echo "  1. Restore backup: cp packages/graph-api/.env.backup.* packages/graph-api/.env"
echo "  2. Or manually change NEO4J_URI to: bolt://localhost:7687"
echo ""
echo "Next step: Test the connection!"
