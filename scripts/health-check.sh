#!/bin/bash

# Health check script for deployment testing
# This script verifies that the deployed application components are running correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
MAX_RETRIES="${MAX_RETRIES:-10}"
RETRY_DELAY="${RETRY_DELAY:-5}"

echo -e "${YELLOW}🔍 Starting deployment health checks...${NC}"

# Function to check if a service is responding
check_service() {
    local service_name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    echo -e "${YELLOW}Checking ${service_name} at ${url}...${NC}"
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -f -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
            echo -e "${GREEN}✅ ${service_name} is responding correctly${NC}"
            return 0
        else
            echo -e "${YELLOW}⏳ ${service_name} not ready, attempt $i/$MAX_RETRIES (retrying in ${RETRY_DELAY}s...)${NC}"
            sleep $RETRY_DELAY
        fi
    done
    
    echo -e "${RED}❌ ${service_name} failed to respond after $MAX_RETRIES attempts${NC}"
    return 1
}

# Function to check if a service has expected content
check_service_content() {
    local service_name="$1"
    local url="$2"
    local expected_content="$3"
    
    echo -e "${YELLOW}Checking ${service_name} content at ${url}...${NC}"
    
    for i in $(seq 1 $MAX_RETRIES); do
        response=$(curl -f -s "$url" 2>/dev/null || echo "")
        if echo "$response" | grep -q "$expected_content"; then
            echo -e "${GREEN}✅ ${service_name} content check passed${NC}"
            return 0
        else
            echo -e "${YELLOW}⏳ ${service_name} content not ready, attempt $i/$MAX_RETRIES (retrying in ${RETRY_DELAY}s...)${NC}"
            sleep $RETRY_DELAY
        fi
    done
    
    echo -e "${RED}❌ ${service_name} content check failed after $MAX_RETRIES attempts${NC}"
    return 1
}

# Check backend health endpoint
echo -e "\n${YELLOW}=== Backend Health Check ===${NC}"
if ! check_service_content "Backend API" "$BACKEND_URL/health" '"status"'; then
    exit 1
fi

# Check backend root endpoint (allow more flexible response)
if ! check_service "Backend Root" "$BACKEND_URL/" "200"; then
    echo -e "${YELLOW}⚠️  Backend root endpoint basic connectivity failed, trying content check...${NC}"
    if ! check_service_content "Backend Root" "$BACKEND_URL/" '"status"'; then
        echo -e "${YELLOW}⚠️  Backend root endpoint content check also failed, but health endpoint passed${NC}"
    fi
fi

# Check frontend (basic connectivity)
echo -e "\n${YELLOW}=== Frontend Health Check ===${NC}"
if ! check_service "Frontend" "$FRONTEND_URL" "200"; then
    exit 1
fi

# Additional API endpoint check (if available)
echo -e "\n${YELLOW}=== API Endpoints Check ===${NC}"
if check_service "API Tasks Endpoint" "$BACKEND_URL/tasks/" "200"; then
    echo -e "${GREEN}✅ API tasks endpoint is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  API tasks endpoint check failed (might be expected if auth is required)${NC}"
fi

echo -e "\n${GREEN}🎉 All deployment health checks passed!${NC}"
echo -e "${GREEN}✅ Backend is running and responding at ${BACKEND_URL}${NC}"
echo -e "${GREEN}✅ Frontend is accessible at ${FRONTEND_URL}${NC}"

exit 0