#!/bin/bash
# This script runs on the GCE VM during startup
set -e

echo "Starting Neo4j installation on GCE VM..." | tee -a /var/log/neo4j-install.log

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
echo "Installing dependencies..." | tee -a /var/log/neo4j-install.log
apt-get install -y \
    wget \
    curl \
    gnupg \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    openjdk-17-jre-headless

# Add Neo4j repository
echo "Adding Neo4j repository..." | tee -a /var/log/neo4j-install.log
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | tee /etc/apt/sources.list.d/neo4j.list

# Update and install Neo4j
apt-get update
echo "Installing Neo4j 5.14..." | tee -a /var/log/neo4j-install.log
apt-get install -y neo4j=1:5.14.0

# Configure Neo4j
echo "Configuring Neo4j..." | tee -a /var/log/neo4j-install.log

# Backup original config
cp /etc/neo4j/neo4j.conf /etc/neo4j/neo4j.conf.backup

# Set memory configuration (matching current Docker setup)
cat >> /etc/neo4j/neo4j.conf << 'EOF'

# Memory Configuration
server.memory.heap.initial_size=2g
server.memory.heap.max_size=4g
server.memory.pagecache.size=2g

# Network Configuration
server.default_listen_address=0.0.0.0
server.bolt.listen_address=0.0.0.0:7687
server.http.listen_address=0.0.0.0:7474

# Transaction Configuration
db.transaction.timeout=120s

# APOC Configuration
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*
EOF

# Download and install APOC plugin
echo "Installing APOC plugin..." | tee -a /var/log/neo4j-install.log
APOC_VERSION="5.14.0"
wget -P /var/lib/neo4j/plugins https://github.com/neo4j/apoc/releases/download/${APOC_VERSION}/apoc-${APOC_VERSION}-core.jar

# Set permissions
chown -R neo4j:neo4j /var/lib/neo4j/plugins

# Set initial password
echo "Setting Neo4j password..." | tee -a /var/log/neo4j-install.log
neo4j-admin dbms set-initial-password canadagpt2024 || true

# Enable and start Neo4j
echo "Starting Neo4j service..." | tee -a /var/log/neo4j-install.log
systemctl enable neo4j
systemctl start neo4j

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to start..." | tee -a /var/log/neo4j-install.log
for i in {1..30}; do
    if systemctl is-active --quiet neo4j; then
        echo "Neo4j is running" | tee -a /var/log/neo4j-install.log
        break
    fi
    sleep 2
done

# Install gsutil (for downloading backup)
echo "Installing Google Cloud SDK..." | tee -a /var/log/neo4j-install.log
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
apt-get update
apt-get install -y google-cloud-cli

# Create backup directories
mkdir -p /var/backups/neo4j
chown neo4j:neo4j /var/backups/neo4j

# Mark installation as complete
touch /tmp/neo4j-install-complete

echo "Neo4j installation complete!" | tee -a /var/log/neo4j-install.log
echo "Neo4j version: $(neo4j --version)" | tee -a /var/log/neo4j-install.log
echo "Installation log: /var/log/neo4j-install.log"
