#!/bin/bash
# Deployment Verification Script
# Tests connectivity between Netlify frontend and Render backend

echo "🔍 Verifying Netlify/Render Deployment..."
echo ""

# Configuration
BACKEND_URL="https://content-backend-flmx.onrender.com"
NETLIFY_URL="YOUR_NETLIFY_URL_HERE"  # Replace with actual Netlify URL

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Backend Health
echo "1️⃣ Testing backend health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✅ Backend is running${NC}"
    echo "   Response: $HEALTH_BODY"
else
    echo -e "${RED}❌ Backend not responding (HTTP $HTTP_CODE)${NC}"
    echo "   Fix: Check Render dashboard → Your service → Logs"
    exit 1
fi
echo ""

# Test 2: CORS Headers
echo "2️⃣ Testing CORS configuration..."
CORS_HEADERS=$(curl -s -I "$BACKEND_URL/health" | grep -i "access-control")

if [ -n "$CORS_HEADERS" ]; then
    echo -e "${GREEN}✅ CORS headers present${NC}"
    echo "$CORS_HEADERS" | sed 's/^/   /'
else
    echo -e "${RED}❌ CORS headers missing${NC}"
    echo "   Fix: Add CORS_ORIGINS to Render environment variables"
    echo "   Example: CORS_ORIGINS=$NETLIFY_URL,http://localhost:5173"
fi
echo ""

# Test 3: Auth Endpoint
echo "3️⃣ Testing auth endpoint reachability..."
AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}')
HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
AUTH_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 401 ] || [ "$HTTP_CODE" -eq 422 ]; then
    echo -e "${GREEN}✅ Auth endpoint is working${NC}"
    echo "   (401/422 expected for invalid credentials)"
elif [ "$HTTP_CODE" -eq 404 ]; then
    echo -e "${RED}❌ Auth endpoint not found${NC}"
    echo "   Fix: Check backend router configuration"
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_CODE)${NC}"
    echo "   Response: $AUTH_BODY"
fi
echo ""

# Test 4: CORS Preflight
echo "4️⃣ Testing CORS preflight from Netlify origin..."
if [ "$NETLIFY_URL" != "YOUR_NETLIFY_URL_HERE" ]; then
    PREFLIGHT=$(curl -s -X OPTIONS "$BACKEND_URL/api/auth/login" \
        -H "Origin: $NETLIFY_URL" \
        -H "Access-Control-Request-Method: POST" \
        -i | grep -i "access-control-allow-origin")

    if echo "$PREFLIGHT" | grep -q "$NETLIFY_URL"; then
        echo -e "${GREEN}✅ CORS allows Netlify origin${NC}"
    elif echo "$PREFLIGHT" | grep -q "\*"; then
        echo -e "${GREEN}✅ CORS allows all origins${NC}"
    else
        echo -e "${RED}❌ Netlify origin not allowed${NC}"
        echo "   Fix: Add $NETLIFY_URL to CORS_ORIGINS on Render"
        echo "   Current CORS header: $PREFLIGHT"
    fi
else
    echo -e "${YELLOW}⚠️  Skipped (set NETLIFY_URL in script)${NC}"
fi
echo ""

# Summary
echo "📋 Summary:"
echo "   Backend URL: $BACKEND_URL"
echo "   Netlify URL: $NETLIFY_URL"
echo ""
echo "💡 Next steps if errors found:"
echo "   1. Check DEPLOYMENT_DIAGNOSTICS.md for detailed fixes"
echo "   2. Verify environment variables in Netlify and Render dashboards"
echo "   3. Trigger new deployment on Netlify (clear cache)"
echo "   4. Check browser console for specific error messages"
