#!/bin/bash

#
# Setup script for local Neo4j development database
# Starts Neo4j in Docker and applies schema
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CanadaGPT - Neo4j Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    echo "Please run this script from the repository root"
    exit 1
fi

# Start Neo4j
echo -e "${YELLOW}🚀 Starting Neo4j container...${NC}"
docker-compose up -d neo4j

# Wait for Neo4j to be ready
echo -e "${YELLOW}⏳ Waiting for Neo4j to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec canadagpt-neo4j cypher-shell -u neo4j -p canadagpt2024 "RETURN 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Neo4j is ready!${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Neo4j failed to start after $MAX_RETRIES attempts${NC}"
    echo "Check logs with: docker-compose logs neo4j"
    exit 1
fi

echo ""

# Apply schema
echo -e "${YELLOW}📋 Applying Neo4j schema...${NC}"
if [ -f "docs/neo4j-schema.cypher" ]; then
    docker exec -i canadagpt-neo4j cypher-shell -u neo4j -p canadagpt2024 < docs/neo4j-schema.cypher
    echo -e "${GREEN}✅ Schema applied successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Schema file not found (docs/neo4j-schema.cypher)${NC}"
    echo "You can apply it manually later"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Neo4j Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Connection Details:${NC}"
echo "  Browser UI:   ${GREEN}http://localhost:7474${NC}"
echo "  Bolt URI:     ${GREEN}bolt://localhost:7687${NC}"
echo "  Username:     ${GREEN}neo4j${NC}"
echo "  Password:     ${GREEN}canadagpt2024${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Open ${GREEN}http://localhost:7474${NC} in your browser"
echo "  2. Create .env file in packages/data-pipeline/"
echo "  3. Run: ${YELLOW}canadagpt-ingest --test${NC} to verify connection"
echo "  4. Run: ${YELLOW}canadagpt-ingest --parliament${NC} to load data"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:    ${YELLOW}docker-compose logs -f neo4j${NC}"
echo "  Stop Neo4j:   ${YELLOW}docker-compose down${NC}"
echo "  Reset data:   ${YELLOW}docker-compose down -v${NC} (WARNING: deletes all data)"
echo ""
