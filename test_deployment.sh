#!/bin/bash
# Test script for single-service deployment

echo "========================================="
echo "Testing Single-Service Deployment"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if container is running
echo ""
echo "1. Checking container status..."
if docker ps | grep -q "content-jumpstart-api"; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}✗ Container is not running${NC}"
    echo "Starting container..."
    docker-compose up -d api
    sleep 10
fi

# 2. Test health endpoint (API)
echo ""
echo "2. Testing health endpoint (API)..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health endpoint working${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
fi

# 3. Test root endpoint (Frontend)
echo ""
echo "3. Testing root endpoint (Frontend)..."
ROOT_RESPONSE=$(curl -s http://localhost:8000/)
if echo "$ROOT_RESPONSE" | grep -q "root"; then
    echo -e "${GREEN}✓ Frontend HTML served${NC}"
    echo "Found <div id=\"root\"> in response"
else
    echo -e "${RED}✗ Frontend HTML not found${NC}"
    echo "Response (first 200 chars): ${ROOT_RESPONSE:0:200}"
fi

# 4. Test API endpoint
echo ""
echo "4. Testing API endpoint..."
API_HEALTH=$(curl -s http://localhost:8000/api/health)
if echo "$API_HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API endpoint working${NC}"
else
    echo -e "${RED}✗ API endpoint failed${NC}"
fi

# 5. Check frontend files in container
echo ""
echo "5. Checking frontend files in container..."
FRONTEND_FILES=$(docker exec content-jumpstart-api ls -la /app/operator-dashboard/dist 2>&1)
if echo "$FRONTEND_FILES" | grep -q "index.html"; then
    echo -e "${GREEN}✓ Frontend files found in container${NC}"
    echo "$FRONTEND_FILES"
else
    echo -e "${RED}✗ Frontend files NOT found in container${NC}"
    echo "$FRONTEND_FILES"
fi

# 6. Test API documentation
echo ""
echo "6. Testing API documentation..."
DOCS_RESPONSE=$(curl -s http://localhost:8000/docs)
if echo "$DOCS_RESPONSE" | grep -q "swagger"; then
    echo -e "${GREEN}✓ API docs accessible${NC}"
else
    echo -e "${YELLOW}⚠ API docs may not be accessible${NC}"
fi

# 7. Check container logs for errors
echo ""
echo "7. Checking container logs for errors..."
ERROR_LOGS=$(docker logs content-jumpstart-api 2>&1 | grep -i "error\|warning\|failed" | tail -5)
if [ -z "$ERROR_LOGS" ]; then
    echo -e "${GREEN}✓ No errors in logs${NC}"
else
    echo -e "${YELLOW}⚠ Found warnings/errors in logs:${NC}"
    echo "$ERROR_LOGS"
fi

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Container: http://localhost:8000"
echo "API Health: http://localhost:8000/api/health"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "If all tests passed, your single-service deployment is working!"
echo "Access the frontend at: http://localhost:8000"
