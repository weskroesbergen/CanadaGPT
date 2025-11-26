#!/bin/bash
#
# dev-stop.sh - Stop Development Environment
#
# Gracefully stops all CanadaGPT development services:
#   - SSH tunnel to production Neo4j
#   - GraphQL API (port 4000)
#   - Frontend (port 3000)
#
# Usage:
#   ./scripts/dev-stop.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}🛑 Stopping CanadaGPT Development Environment${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

STOPPED_COUNT=0
FAILED_COUNT=0

# Function to gracefully stop a process on a specific port
stop_port() {
    local PORT=$1
    local SERVICE_NAME=$2

    echo -e "${BLUE}🔍 Checking for $SERVICE_NAME on port $PORT...${NC}"

    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        PID=$(lsof -ti:$PORT)
        echo -e "${YELLOW}   Found $SERVICE_NAME (PID: $PID)${NC}"
        echo -e "${BLUE}   Sending TERM signal...${NC}"

        kill -TERM $PID 2>/dev/null || true

        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 $PID 2>/dev/null; then
                echo -e "${GREEN}   ✅ $SERVICE_NAME stopped gracefully${NC}"
                STOPPED_COUNT=$((STOPPED_COUNT + 1))
                echo ""
                return 0
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo -e "${YELLOW}   Process didn't stop gracefully, forcing...${NC}"
            kill -9 $PID 2>/dev/null || true
            sleep 1

            if ! kill -0 $PID 2>/dev/null; then
                echo -e "${GREEN}   ✅ $SERVICE_NAME stopped (forced)${NC}"
                STOPPED_COUNT=$((STOPPED_COUNT + 1))
            else
                echo -e "${RED}   ❌ Failed to stop $SERVICE_NAME${NC}"
                FAILED_COUNT=$((FAILED_COUNT + 1))
            fi
        fi
    else
        echo -e "${BLUE}   ℹ️  $SERVICE_NAME not running${NC}"
    fi
    echo ""
}

# Stop Frontend (port 3000)
stop_port 3000 "Frontend"

# Stop GraphQL API (port 4000)
stop_port 4000 "GraphQL API"

# Stop SSH Tunnel (port 7687)
echo -e "${BLUE}🔍 Checking for SSH Tunnel on port 7687...${NC}"
if lsof -Pi :7687 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    PID=$(lsof -ti:7687)
    echo -e "${YELLOW}   Found SSH Tunnel (PID: $PID)${NC}"
    echo -e "${BLUE}   Sending TERM signal...${NC}"

    kill -TERM $PID 2>/dev/null || true

    # Wait up to 5 seconds for tunnel to close
    for i in {1..5}; do
        if ! kill -0 $PID 2>/dev/null; then
            echo -e "${GREEN}   ✅ SSH Tunnel stopped gracefully${NC}"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
            echo ""
            break
        fi
        sleep 1
    done

    # Force kill if still running
    if kill -0 $PID 2>/dev/null; then
        echo -e "${YELLOW}   Tunnel didn't stop gracefully, forcing...${NC}"
        kill -9 $PID 2>/dev/null || true
        sleep 1

        if ! kill -0 $PID 2>/dev/null; then
            echo -e "${GREEN}   ✅ SSH Tunnel stopped (forced)${NC}"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
        else
            echo -e "${RED}   ❌ Failed to stop SSH Tunnel${NC}"
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
    fi
else
    echo -e "${BLUE}   ℹ️  SSH Tunnel not running${NC}"
fi
echo ""

# Clean up any pnpm processes that might be lingering
echo -e "${BLUE}🧹 Cleaning up any lingering pnpm processes...${NC}"
PNPM_PIDS=$(pgrep -f "pnpm dev" || true)
if [ -n "$PNPM_PIDS" ]; then
    echo -e "${YELLOW}   Found pnpm processes: $PNPM_PIDS${NC}"
    echo "$PNPM_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2

    # Force kill any remaining
    PNPM_PIDS=$(pgrep -f "pnpm dev" || true)
    if [ -n "$PNPM_PIDS" ]; then
        echo "$PNPM_PIDS" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}   ✅ Cleaned up lingering pnpm processes${NC}"
    else
        echo -e "${GREEN}   ✅ pnpm processes stopped${NC}"
    fi
else
    echo -e "${BLUE}   ℹ️  No lingering pnpm processes found${NC}"
fi
echo ""

# Clean up any gcloud SSH processes
echo -e "${BLUE}🧹 Cleaning up any lingering gcloud SSH processes...${NC}"
GCLOUD_PIDS=$(pgrep -f "gcloud compute ssh canadagpt-neo4j" || true)
if [ -n "$GCLOUD_PIDS" ]; then
    echo -e "${YELLOW}   Found gcloud SSH processes: $GCLOUD_PIDS${NC}"
    echo "$GCLOUD_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2

    # Force kill any remaining
    GCLOUD_PIDS=$(pgrep -f "gcloud compute ssh canadagpt-neo4j" || true)
    if [ -n "$GCLOUD_PIDS" ]; then
        echo "$GCLOUD_PIDS" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}   ✅ Cleaned up lingering gcloud SSH processes${NC}"
    else
        echo -e "${GREEN}   ✅ gcloud SSH processes stopped${NC}"
    fi
else
    echo -e "${BLUE}   ℹ️  No lingering gcloud SSH processes found${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILED_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ Development environment stopped successfully!${NC}"
    if [ $STOPPED_COUNT -eq 0 ]; then
        echo -e "${BLUE}   (No services were running)${NC}"
    else
        echo -e "${GREEN}   Stopped $STOPPED_COUNT service(s)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Development environment stopped with $FAILED_COUNT error(s)${NC}"
    echo -e "${YELLOW}   You may need to manually check for lingering processes${NC}"
fi
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit $FAILED_COUNT
