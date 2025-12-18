# Netlify/Render Connection Diagnostics

## Issue
Frontend deployed on Netlify cannot reach backend deployed on Render.

## Quick Diagnosis Checklist

### 1. Verify Backend is Running

```bash
# Test backend health endpoint
curl https://content-backend-flmx.onrender.com/health

# Expected response:
{"status":"healthy","timestamp":"2025-12-18T..."}

# Test auth endpoint is reachable
curl -X POST https://content-backend-flmx.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrong"}'

# Expected response (401 error is good - means endpoint is working):
{"detail":"Incorrect email or password"}
```

**If these fail:** Backend is not running or URL is incorrect.

### 2. Check Netlify Environment Variables

**Required variables in Netlify dashboard:**

```bash
VITE_API_URL=https://content-backend-flmx.onrender.com
VITE_USE_MOCKS=false
```

**How to check:**
1. Go to Netlify dashboard → Your site → Site settings → Environment variables
2. Verify `VITE_API_URL` is set to your Render backend URL
3. Verify `VITE_USE_MOCKS` is `false` (or not set)

**Common mistake:** Environment variables in Netlify must be set in the dashboard, not just in `.env.production`. The `.env.production` file is NOT read during Netlify builds unless you configure it.

### 3. Check Render Environment Variables

**Required variables in Render dashboard:**

```bash
CORS_ORIGINS=https://your-netlify-app.netlify.app,https://other-domain.com
SECRET_KEY=<your-secret-key>
ANTHROPIC_API_KEY=<your-api-key>
DATABASE_URL=<postgres-connection-string>
```

**How to check:**
1. Go to Render dashboard → Your service → Environment
2. Verify `CORS_ORIGINS` includes your Netlify URL
3. Verify `SECRET_KEY` is set (32+ character random string)

**Common mistake:** Forgot to add Netlify URL to CORS_ORIGINS after deploying frontend.

### 4. Browser Console Errors

Open browser console (F12) on Netlify site and look for:

```javascript
// CORS error (backend missing frontend URL in CORS_ORIGINS):
Access to XMLHttpRequest at 'https://content-backend-flmx.onrender.com/api/auth/login'
from origin 'https://your-app.netlify.app' has been blocked by CORS policy

// Network error (backend not running or URL wrong):
Failed to fetch
net::ERR_NAME_NOT_RESOLVED

// Wrong API URL (VITE_API_URL not set):
POST http://localhost:8000/api/auth/login 404 (Not Found)
```

### 5. Network Tab Analysis

1. Open browser DevTools → Network tab
2. Try to login
3. Find the `/api/auth/login` request
4. Check:
   - **Request URL:** Should be `https://content-backend-flmx.onrender.com/api/auth/login`
   - **Status:** Should NOT be 0 or (failed)
   - **Response Headers:** Should include `access-control-allow-origin`

## Common Fixes

### Fix 1: Set Netlify Environment Variables

**Netlify Dashboard:**
1. Go to: Site settings → Environment variables → Add a variable
2. Add: `VITE_API_URL` = `https://content-backend-flmx.onrender.com`
3. Add: `VITE_USE_MOCKS` = `false`
4. Click "Save"
5. **IMPORTANT:** Go to Deploys → Trigger deploy → Clear cache and deploy site

**Why clear cache?** Vite embeds environment variables at build time. Old cached builds won't have the new values.

### Fix 2: Update Render CORS_ORIGINS

**Render Dashboard:**
1. Go to: Your service → Environment
2. Find `CORS_ORIGINS` variable
3. Update value to include your Netlify URL:
   ```
   https://your-actual-app.netlify.app,http://localhost:5173,http://localhost:3000
   ```
4. Click "Save Changes"
5. **Render will auto-restart** the service

**Note:** Get your exact Netlify URL from: Netlify dashboard → Your site → Site overview → (look for "https://your-app.netlify.app")

### Fix 3: Verify Backend Configuration

**Check Render logs:**
1. Render dashboard → Your service → Logs
2. Look for startup errors like:
   ```
   SECRET_KEY validation failed
   ANTHROPIC_API_KEY not set
   Database connection failed
   ```

**If SECRET_KEY error:**
```bash
# Generate a new secure key:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to Render environment variables
```

### Fix 4: Test Backend Independently

Before troubleshooting frontend, verify backend works:

```bash
# Test health endpoint
curl https://content-backend-flmx.onrender.com/health

# Test authentication with real credentials
curl -X POST https://content-backend-flmx.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-test-user@example.com",
    "password": "your-test-password"
  }'

# Expected response (if credentials correct):
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {...}
}
```

## Verification Script

After making fixes, verify the connection:

```bash
# 1. Backend health
curl -f https://content-backend-flmx.onrender.com/health || echo "❌ Backend not responding"

# 2. CORS headers present
curl -I https://content-backend-flmx.onrender.com/health | grep -i "access-control" || echo "❌ CORS not configured"

# 3. Auth endpoint reachable
curl -X POST https://content-backend-flmx.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}' \
  | grep -q "detail" && echo "✅ Auth endpoint working" || echo "❌ Auth endpoint not responding"
```

## Most Likely Issue

**Based on your error description, the most likely cause is:**

**Option A: VITE_API_URL not set on Netlify**
- Symptom: Browser console shows requests going to `http://localhost:8000`
- Fix: Add `VITE_API_URL` environment variable in Netlify dashboard

**Option B: Netlify URL missing from CORS_ORIGINS**
- Symptom: Browser console shows CORS policy error
- Fix: Add Netlify URL to `CORS_ORIGINS` in Render dashboard

**Option C: Both**
- Symptom: Mixed errors or no network requests visible
- Fix: Apply both fixes above

## Next Steps

1. **Check browser console** for exact error message
2. **Apply Fix 1 and Fix 2** above
3. **Clear cache and redeploy** both services
4. **Test again**

If issue persists after these fixes, the problem may be:
- Render service is sleeping (free tier) - first request wakes it up (30s delay)
- Network/firewall issue blocking Render domain
- Render service failed to start (check Render logs)
