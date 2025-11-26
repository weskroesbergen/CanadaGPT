#!/bin/bash
#
# check-dev-status.sh - Check Development Environment Status
#
# Performs health checks on all CanadaGPT development services:
#   - SSH tunnel to production Neo4j
#   - GraphQL API (port 4000)
#   - Frontend (port 3000)
#   - Neo4j connectivity
#
# Usage:
#   ./scripts/check-dev-status.sh
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🔍 CanadaGPT Development Environment Status${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

HEALTHY=0
UNHEALTHY=0

# Function to check if a port is listening
check_port() {
    local PORT=$1
    local SERVICE_NAME=$2

    echo -e "${BLUE}🔍 Checking $SERVICE_NAME (port $PORT)...${NC}"

    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        PID=$(lsof -ti:$PORT)
        echo -e "${GREEN}   ✅ Running (PID: $PID)${NC}"
        HEALTHY=$((HEALTHY + 1))
        return 0
    else
        echo -e "${RED}   ❌ Not running${NC}"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
}

# Function to check HTTP endpoint
check_http() {
    local URL=$1
    local SERVICE_NAME=$2

    if command -v curl >/dev/null 2>&1 ; then
        if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$URL" | grep -q "^[23]"; then
            echo -e "${GREEN}   ✅ Responding to HTTP requests${NC}"
            return 0
        else
            echo -e "${YELLOW}   ⚠️  Port open but not responding to HTTP${NC}"
            return 1
        fi
    fi
    return 0
}

# Check SSH Tunnel
echo ""
if check_port 7687 "SSH Tunnel to Neo4j"; then
    # Try to verify Neo4j connectivity
    echo -e "${BLUE}   🔌 Testing Neo4j connectivity...${NC}"

    # Check if we can reach the Neo4j bolt port
    if timeout 2 bash -c "</dev/tcp/localhost/7687" 2>/dev/null; then
        echo -e "${GREEN}   ✅ Neo4j connection available${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Neo4j connection test failed${NC}"
    fi
fi
echo ""

# Check GraphQL API
if check_port 4000 "GraphQL API"; then
    echo -e "${BLUE}   🔌 Testing GraphQL endpoint...${NC}"
    check_http "http://localhost:4000/graphql" "GraphQL API"

    # Check if log file exists
    if [ -f "/tmp/canadagpt-graphql.log" ]; then
        LOG_SIZE=$(wc -l < /tmp/canadagpt-graphql.log)
        echo -e "${CYAN}   📝 Log file: /tmp/canadagpt-graphql.log ($LOG_SIZE lines)${NC}"

        # Check for recent errors
        if tail -20 /tmp/canadagpt-graphql.log 2>/dev/null | grep -i "error" >/dev/null; then
            echo -e "${YELLOW}   ⚠️  Recent errors found in log${NC}"
        fi
    fi
fi
echo ""

# Check Frontend
if check_port 3000 "Frontend"; then
    echo -e "${BLUE}   🔌 Testing frontend endpoint...${NC}"
    check_http "http://localhost:3000" "Frontend"

    # Check if log file exists
    if [ -f "/tmp/canadagpt-frontend.log" ]; then
        LOG_SIZE=$(wc -l < /tmp/canadagpt-frontend.log)
        echo -e "${CYAN}   📝 Log file: /tmp/canadagpt-frontend.log ($LOG_SIZE lines)${NC}"

        # Check for recent errors
        if tail -20 /tmp/canadagpt-frontend.log 2>/dev/null | grep -i "error" >/dev/null; then
            echo -e "${YELLOW}   ⚠️  Recent errors found in log${NC}"
        fi
    fi
fi
echo ""

# Service URLs
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📍 Service URLs${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if lsof -Pi :7687 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "  ${GREEN}🗄️  Neo4j:${NC}       bolt://localhost:7687 (via SSH tunnel)"
else
    echo -e "  ${RED}🗄️  Neo4j:${NC}       bolt://localhost:7687 ${RED}(tunnel not running)${NC}"
fi

if lsof -Pi :4000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "  ${GREEN}🔌 GraphQL API:${NC}  http://localhost:4000/graphql"
else
    echo -e "  ${RED}🔌 GraphQL API:${NC}  http://localhost:4000/graphql ${RED}(not running)${NC}"
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "  ${GREEN}🌐 Frontend:${NC}     http://localhost:3000"
else
    echo -e "  ${RED}🌐 Frontend:${NC}     http://localhost:3000 ${RED}(not running)${NC}"
fi

echo -e "  ${BLUE}💾 Supabase:${NC}     https://pbxyhcdzdovsdlsyixsk.supabase.co (production)"
echo ""

# Log files
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📝 Log Files${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "/tmp/canadagpt-graphql.log" ]; then
    echo -e "  ${BLUE}GraphQL:${NC}  tail -f /tmp/canadagpt-graphql.log"
else
    echo -e "  ${BLUE}GraphQL:${NC}  /tmp/canadagpt-graphql.log ${YELLOW}(not found)${NC}"
fi

if [ -f "/tmp/canadagpt-frontend.log" ]; then
    echo -e "  ${BLUE}Frontend:${NC} tail -f /tmp/canadagpt-frontend.log"
else
    echo -e "  ${BLUE}Frontend:${NC} /tmp/canadagpt-frontend.log ${YELLOW}(not found)${NC}"
fi
echo ""

# Summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

TOTAL=$((HEALTHY + UNHEALTHY))

if [ $UNHEALTHY -eq 0 ]; then
    echo -e "${GREEN}✅ All services healthy ($HEALTHY/$TOTAL)${NC}"
    echo ""
    echo -e "${GREEN}Ready to develop!${NC}"
elif [ $HEALTHY -eq 0 ]; then
    echo -e "${RED}❌ No services running${NC}"
    echo ""
    echo -e "${YELLOW}To start the development environment:${NC}"
    echo -e "  ${BLUE}./scripts/dev-start.sh${NC}"
else
    echo -e "${YELLOW}⚠️  Some services not running ($HEALTHY/$TOTAL healthy)${NC}"
    echo ""
    echo -e "${YELLOW}To start missing services:${NC}"

    if ! lsof -Pi :7687 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "  ${BLUE}SSH Tunnel:${NC} ./scripts/dev-tunnel.sh &"
    fi

    if ! lsof -Pi :4000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "  ${BLUE}GraphQL API:${NC} cd packages/graph-api && pnpm dev"
    fi

    if ! lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "  ${BLUE}Frontend:${NC}    cd packages/frontend && pnpm dev"
    fi

    echo ""
    echo -e "${YELLOW}Or start all services:${NC}"
    echo -e "  ${BLUE}./scripts/dev-start.sh${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Exit with error code if any services are unhealthy
exit $UNHEALTHY
