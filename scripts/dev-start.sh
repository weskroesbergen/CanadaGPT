#!/bin/bash
#
# dev-start.sh - Start Complete Development Environment
#
# One-command startup for the entire CanadaGPT development stack:
#   - SSH tunnel to production Neo4j
#   - GraphQL API (port 4000)
#   - Frontend (port 3000)
#
# Usage:
#   ./scripts/dev-start.sh
#
# Press Ctrl+C to stop all services gracefully
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/.." && pwd )"

# PID tracking
TUNNEL_PID=""
GRAPHQL_PID=""
FRONTEND_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🛑 Shutting down development environment...${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ -n "$FRONTEND_PID" ]; then
        echo -e "${BLUE}Stopping Frontend (PID: $FRONTEND_PID)...${NC}"
        kill -TERM $FRONTEND_PID 2>/dev/null || true
    fi

    if [ -n "$GRAPHQL_PID" ]; then
        echo -e "${BLUE}Stopping GraphQL API (PID: $GRAPHQL_PID)...${NC}"
        kill -TERM $GRAPHQL_PID 2>/dev/null || true
    fi

    if [ -n "$TUNNEL_PID" ]; then
        echo -e "${BLUE}Stopping SSH Tunnel (PID: $TUNNEL_PID)...${NC}"
        kill -TERM $TUNNEL_PID 2>/dev/null || true
    fi

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill any remaining processes
    if [ -n "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill -9 $FRONTEND_PID 2>/dev/null || true
    fi
    if [ -n "$GRAPHQL_PID" ] && kill -0 $GRAPHQL_PID 2>/dev/null; then
        kill -9 $GRAPHQL_PID 2>/dev/null || true
    fi
    if [ -n "$TUNNEL_PID" ] && kill -0 $TUNNEL_PID 2>/dev/null; then
        kill -9 $TUNNEL_PID 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}✅ All services stopped${NC}"
    echo ""
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🚀 CanadaGPT Development Environment${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if tunnel is already running
echo -e "${BLUE}🔍 Checking for existing SSH tunnel...${NC}"
if lsof -Pi :7687 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    EXISTING_PID=$(lsof -ti:7687)
    echo -e "${GREEN}✅ SSH tunnel already running (PID: $EXISTING_PID)${NC}"
    TUNNEL_PID=$EXISTING_PID
else
    echo -e "${YELLOW}⚠️  No SSH tunnel detected${NC}"
    echo -e "${BLUE}🚇 Starting SSH tunnel in background...${NC}"

    # Start tunnel in background
    "${SCRIPT_DIR}/dev-tunnel.sh" &
    TUNNEL_PID=$!

    echo -e "${CYAN}   Tunnel PID: $TUNNEL_PID${NC}"
    echo -e "${CYAN}   Waiting for tunnel to establish (5s)...${NC}"
    sleep 5

    # Verify tunnel started
    if ! kill -0 $TUNNEL_PID 2>/dev/null; then
        echo -e "${RED}❌ Failed to start SSH tunnel${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ SSH tunnel established${NC}"
fi
echo ""

# Start GraphQL API
echo -e "${BLUE}📊 Starting GraphQL API...${NC}"
cd "${PROJECT_ROOT}/packages/graph-api"

# Kill any existing process on port 4000
if lsof -Pi :4000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    EXISTING_PID=$(lsof -ti:4000)
    echo -e "${YELLOW}   Killing existing process on port 4000 (PID: $EXISTING_PID)...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

pnpm dev > /tmp/canadagpt-graphql.log 2>&1 &
GRAPHQL_PID=$!

echo -e "${CYAN}   GraphQL PID: $GRAPHQL_PID${NC}"
echo -e "${CYAN}   Waiting for GraphQL API to start (3s)...${NC}"
sleep 3

if ! kill -0 $GRAPHQL_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start GraphQL API${NC}"
    echo -e "${RED}Check logs: tail -f /tmp/canadagpt-graphql.log${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}✅ GraphQL API started${NC}"
echo ""

# Start Frontend
echo -e "${BLUE}🌐 Starting Frontend...${NC}"
cd "${PROJECT_ROOT}/packages/frontend"

# Kill any existing process on port 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    EXISTING_PID=$(lsof -ti:3000)
    echo -e "${YELLOW}   Killing existing process on port 3000 (PID: $EXISTING_PID)...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

pnpm dev > /tmp/canadagpt-frontend.log 2>&1 &
FRONTEND_PID=$!

echo -e "${CYAN}   Frontend PID: $FRONTEND_PID${NC}"
echo -e "${CYAN}   Waiting for Frontend to start (5s)...${NC}"
sleep 5

if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start Frontend${NC}"
    echo -e "${RED}Check logs: tail -f /tmp/canadagpt-frontend.log${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}✅ Frontend started${NC}"
echo ""

# Display status
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Development Environment Running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Services:${NC}"
echo -e "  ${BLUE}🗄️  Neo4j:${NC}       bolt://localhost:7687 (via SSH tunnel to production)"
echo -e "  ${BLUE}🔌 GraphQL API:${NC}  http://localhost:4000/graphql"
echo -e "  ${BLUE}🌐 Frontend:${NC}     http://localhost:3000"
echo -e "  ${BLUE}💾 Supabase:${NC}     https://pbxyhcdzdovsdlsyixsk.supabase.co (production)"
echo ""
echo -e "${CYAN}Process IDs:${NC}"
echo -e "  ${BLUE}SSH Tunnel:${NC}  $TUNNEL_PID"
echo -e "  ${BLUE}GraphQL API:${NC} $GRAPHQL_PID"
echo -e "  ${BLUE}Frontend:${NC}    $FRONTEND_PID"
echo ""
echo -e "${CYAN}Logs:${NC}"
echo -e "  ${BLUE}GraphQL:${NC}  tail -f /tmp/canadagpt-graphql.log"
echo -e "  ${BLUE}Frontend:${NC} tail -f /tmp/canadagpt-frontend.log"
echo ""
echo -e "${YELLOW}💡 Press Ctrl+C to stop all services${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Wait for processes (this blocks until Ctrl+C or process exits)
wait $FRONTEND_PID $GRAPHQL_PID $TUNNEL_PID
