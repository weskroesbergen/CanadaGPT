#!/bin/bash
# FedMCP Ingestion VM Setup Script
# This script sets up the complete ingestion environment on the GCP VM

set -e

echo "=================================================="
echo "FedMCP Data Ingestion VM Setup"
echo "=================================================="

# Get current user
USER=$(whoami)
HOME_DIR="/home/$USER"

# Install tmux for persistent sessions
echo "📦 Installing tmux..."
sudo apt-get install -y tmux

# Clone FedMCP repository
echo "📥 Cloning FedMCP repository..."
cd $HOME_DIR
if [ -d "FedMCP" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd FedMCP
    git pull
    cd ..
else
    git clone https://github.com/MattDuf/FedMCP.git
fi

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd $HOME_DIR/FedMCP/packages/data-pipeline
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python packages..."
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    # Install core packages if requirements.txt doesn't exist
    pip install --upgrade pip
    pip install neo4j psycopg2-binary requests beautifulsoup4 lxml tqdm python-dotenv
fi

# Also install packages for root-level scripts
cd $HOME_DIR/FedMCP
pip install neo4j psycopg2-binary requests beautifulsoup4 lxml tqdm python-dotenv

# Create .env file for data pipeline
echo "⚙️  Configuring environment..."
cat > $HOME_DIR/FedMCP/packages/data-pipeline/.env << 'EOF'
# Neo4j GCP Connection (internal IP)
NEO4J_URI=bolt://10.128.0.3:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=canadagpt2024

# PostgreSQL (local)
POSTGRES_URI=postgresql://localhost:5432/openparliament_temp

# Environment
NODE_ENV=production
EOF

# Create log directory
echo "📁 Creating log directory..."
mkdir -p $HOME_DIR/ingestion_logs

# Test Neo4j connection
echo "🔗 Testing Neo4j connection..."
python3 << 'PYEOF'
from neo4j import GraphDatabase
try:
    driver = GraphDatabase.driver(
        'bolt://10.128.0.3:7687',
        auth=('neo4j', 'canadagpt2024')
    )
    driver.verify_connectivity()
    print('✅ Neo4j connection successful!')
    driver.close()
except Exception as e:
    print(f'❌ Neo4j connection failed: {e}')
    exit(1)
PYEOF

# Test PostgreSQL connection
echo "🔗 Testing PostgreSQL connection..."
psql -U postgres -d openparliament_temp -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL connection successful!"
else
    echo "❌ PostgreSQL connection failed"
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Download Lipad data manually from https://www.lipad.ca/data/"
echo "2. Upload to GCS: gsutil cp ~/Downloads/lipad_*.csv gs://canada-gpt-ca-lipad-data/"
echo "3. Download to VM: gsutil -m cp gs://canada-gpt-ca-lipad-data/* $HOME_DIR/lipad_data/"
echo "4. Run: bash $HOME_DIR/FedMCP/scripts/run-full-ingestion.sh"
echo ""
echo "Or run weekly updates only:"
echo "  bash $HOME_DIR/FedMCP/scripts/update-recent-data.sh"
echo ""
