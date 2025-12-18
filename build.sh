#!/bin/bash
# Unified build script for Render deployment
# Builds both frontend and backend in a single service

set -e  # Exit on error

echo "=== Content Jumpstart Unified Build ==="
echo ""

# Step 1: Install backend dependencies
echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt
echo "✅ Python dependencies installed"
echo ""

# Step 2: Build frontend
echo "🎨 Building React frontend..."
cd operator-dashboard

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm ci --prefer-offline --no-audit
echo "✅ Node dependencies installed"

# Build for production
echo "🏗️  Building frontend for production..."
npm run build
echo "✅ Frontend built successfully"

cd ..
echo ""

# Step 3: Verify build output
if [ -d "operator-dashboard/dist" ]; then
    echo "✅ Frontend build output verified: operator-dashboard/dist"
    echo "   Files:"
    ls -lh operator-dashboard/dist/ | head -10
else
    echo "❌ ERROR: Frontend build failed - dist directory not found"
    exit 1
fi

echo ""
echo "=== Build Complete ==="
echo "Backend will serve frontend from operator-dashboard/dist"
echo "No CORS configuration needed (same origin)"
