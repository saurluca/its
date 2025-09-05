#!/bin/bash

# Simple health check script for Docker containers
# This is a lightweight version for testing containerized applications

set -e

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Starting container health checks...${NC}"

# Test backend container health
echo -e "\n${YELLOW}=== Testing Backend Container ===${NC}"
if docker run --rm --network host curlimages/curl:latest \
   curl -f -s --max-time 30 --retry 5 --retry-delay 2 \
   -H "Content-Type: application/json" \
   http://localhost:8000/health | grep -q "status"; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    exit 1
fi

# Test frontend container accessibility
echo -e "\n${YELLOW}=== Testing Frontend Container ===${NC}"
if docker run --rm --network host curlimages/curl:latest \
   curl -f -s --max-time 30 --retry 5 --retry-delay 2 \
   -o /dev/null -w "%{http_code}" \
   http://localhost:3000 | grep -q "200"; then
    echo -e "${GREEN}✅ Frontend accessibility check passed${NC}"
else
    echo -e "${RED}❌ Frontend accessibility check failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 All container health checks passed!${NC}"