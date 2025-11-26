#!/bin/bash
#
# dev-tunnel.sh - SSH Tunnel to Production Neo4j
#
# Establishes an SSH tunnel to the production Neo4j database for local development.
# This allows the local GraphQL API to connect to production data via bolt://localhost:7687
#
# Usage:
#   ./scripts/dev-tunnel.sh
#
# To run in background:
#   ./scripts/dev-tunnel.sh &
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT="canada-gpt-ca"
INSTANCE="canadagpt-neo4j"
ZONE="us-central1-a"
LOCAL_PORT=7687
REMOTE_PORT=7687

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔌 CanadaGPT Development - Neo4j SSH Tunnel${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if tunnel is already running
if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port ${LOCAL_PORT} is already in use${NC}"
    echo ""
    echo "An SSH tunnel or Neo4j instance may already be running."
    echo "Use 'lsof -i :${LOCAL_PORT}' to see what's using the port."
    echo ""
    read -p "Kill existing process and continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PID=$(lsof -ti:${LOCAL_PORT})
        echo -e "${YELLOW}Killing process ${PID}...${NC}"
        kill -9 $PID 2>/dev/null || true
        sleep 1
    else
        echo -e "${RED}Aborting.${NC}"
        exit 1
    fi
fi

# Check if gcloud is authenticated
echo -e "${BLUE}🔐 Checking gcloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q @; then
    echo -e "${RED}❌ Not authenticated with gcloud${NC}"
    echo ""
    echo "Please run: gcloud auth login"
    exit 1
fi

ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo -e "${GREEN}✅ Authenticated as: ${ACCOUNT}${NC}"
echo ""

# Check if instance exists and is running
echo -e "${BLUE}🔍 Checking Neo4j instance status...${NC}"
INSTANCE_STATUS=$(gcloud compute instances describe ${INSTANCE} \
    --project=${PROJECT} \
    --zone=${ZONE} \
    --format="value(status)" 2>/dev/null || echo "NOT_FOUND")

if [ "$INSTANCE_STATUS" = "NOT_FOUND" ]; then
    echo -e "${RED}❌ Instance '${INSTANCE}' not found${NC}"
    echo ""
    echo "Available instances:"
    gcloud compute instances list --project=${PROJECT}
    exit 1
fi

if [ "$INSTANCE_STATUS" != "RUNNING" ]; then
    echo -e "${RED}❌ Instance '${INSTANCE}' is not running (status: ${INSTANCE_STATUS})${NC}"
    echo ""
    read -p "Start the instance? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Starting instance...${NC}"
        gcloud compute instances start ${INSTANCE} --project=${PROJECT} --zone=${ZONE}
        echo -e "${YELLOW}Waiting for instance to start (30s)...${NC}"
        sleep 30
    else
        echo -e "${RED}Aborting.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Instance is running${NC}"
echo ""

# Establish tunnel
echo -e "${BLUE}🚇 Establishing SSH tunnel...${NC}"
echo ""
echo "  Source:      localhost:${LOCAL_PORT}"
echo "  Destination: ${INSTANCE}:${REMOTE_PORT}"
echo "  Project:     ${PROJECT}"
echo "  Zone:        ${ZONE}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to close the tunnel${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Tunnel established! GraphQL API can now connect to Neo4j${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run the tunnel (this will block until Ctrl+C)
gcloud compute ssh ${INSTANCE} \
    --project=${PROJECT} \
    --zone=${ZONE} \
    --ssh-flag="-N" \
    --ssh-flag="-L ${LOCAL_PORT}:localhost:${REMOTE_PORT}" \
    --ssh-flag="-o ServerAliveInterval=60" \
    --ssh-flag="-o ServerAliveCountMax=10"

# This line only runs if the tunnel exits
echo ""
echo -e "${YELLOW}🔌 Tunnel closed${NC}"
