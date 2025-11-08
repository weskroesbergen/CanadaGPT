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
echo "Creating GCE VM for Neo4j"
echo "========================================"
echo ""
echo "VM Configuration:"
echo "  Name: $VM_NAME"
echo "  Machine Type: $VM_MACHINE_TYPE (2 vCPU, 8GB RAM)"
echo "  Disk Size: $VM_DISK_SIZE SSD"
echo "  Zone: $GCP_ZONE"
echo ""

# Check if VM already exists
if gcloud compute instances describe $VM_NAME --zone=$GCP_ZONE &> /dev/null; then
    echo "⚠️  VM already exists: $VM_NAME"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting existing VM..."
        gcloud compute instances delete $VM_NAME --zone=$GCP_ZONE --quiet
        echo "✅ VM deleted"
    else
        echo "Using existing VM"
        gcloud compute instances describe $VM_NAME --zone=$GCP_ZONE --format="value(networkInterfaces[0].networkIP)"
        exit 0
    fi
fi

echo "1️⃣  Creating VM instance..."
gcloud compute instances create $VM_NAME \
    --zone=$GCP_ZONE \
    --machine-type=$VM_MACHINE_TYPE \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=$VM_DISK_SIZE \
    --boot-disk-type=pd-ssd \
    --tags=neo4j,canadagpt \
    --metadata-from-file startup-script=scripts/gcp-migration/neo4j-install.sh

echo "✅ VM created"

echo ""
echo "2️⃣  Waiting for VM to be ready..."
sleep 10

# Get VM IP
VM_INTERNAL_IP=$(gcloud compute instances describe $VM_NAME \
    --zone=$GCP_ZONE \
    --format="value(networkInterfaces[0].networkIP)")

VM_EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME \
    --zone=$GCP_ZONE \
    --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo "✅ VM is ready"
echo ""
echo "VM Details:"
echo "  Internal IP: $VM_INTERNAL_IP"
echo "  External IP: $VM_EXTERNAL_IP"
echo ""

# Save VM IP to config
echo "NEO4J_VM_INTERNAL_IP=$VM_INTERNAL_IP" >> scripts/gcp-migration/.env
echo "NEO4J_VM_EXTERNAL_IP=$VM_EXTERNAL_IP" >> scripts/gcp-migration/.env

echo "3️⃣  Installing Neo4j (this takes 5-10 minutes)..."
echo "   You can monitor progress with:"
echo "   gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command='tail -f /var/log/syslog'"
echo ""
echo "   Waiting for installation to complete..."

# Wait for startup script to complete
for i in {1..60}; do
    if gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --command='test -f /tmp/neo4j-install-complete' &> /dev/null; then
        echo "✅ Neo4j installation complete"
        break
    fi
    echo "   Still installing... ($i/60)"
    sleep 10
done

echo ""
echo "========================================"
echo "✅ VM Created Successfully!"
echo "========================================"
echo ""
echo "VM Details:"
echo "  Name: $VM_NAME"
echo "  Internal IP: $VM_INTERNAL_IP"
echo "  External IP: $VM_EXTERNAL_IP"
echo "  Neo4j Bolt: bolt://$VM_INTERNAL_IP:7687"
echo "  Neo4j Browser: http://$VM_EXTERNAL_IP:7474"
echo ""
echo "Next step: Run ./scripts/gcp-migration/05-restore-database.sh"
