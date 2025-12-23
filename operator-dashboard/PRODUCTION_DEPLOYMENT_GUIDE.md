# Production Deployment Guide

## Preventing "Failed to Fetch Dynamically Imported Module" Errors

This guide explains the comprehensive solution implemented to prevent chunk loading errors in production.

## Problem

When deploying new versions of a React SPA, users who have the app open may encounter:
```
Failed to fetch dynamically imported module: /assets/Component-[hash].js
```

This happens because:
1. User loads HTML file with references to chunks like `Component-abc123.js`
2. New deployment happens, creating `Component-xyz789.js`
3. User navigates to a new page, browser tries to fetch `Component-abc123.js`
4. File doesn't exist anymore → Error

## Comprehensive Solution

### 1. Automatic Chunk Retry (Frontend)

**File:** `src/utils/chunkRetry.ts`

All lazy-loaded components now automatically retry failed imports with exponential backoff:
- **Max retries:** 3 attempts
- **Backoff:** 1s → 2s → 4s
- **Auto-reload:** Page reloads on final failure to fetch fresh HTML

**Usage in router:**
```typescript
import { lazyWithRetry } from '@/utils/chunkRetry';

const Component = lazyWithRetry(() => import('./Component'));
```

### 2. Error Boundary (Frontend)

**File:** `src/components/ErrorBoundary.tsx`

Catches and handles React errors gracefully:
- Detects chunk loading errors specifically
- Shows user-friendly "Update Required" message
- Provides reload button
- Logs errors for debugging

**Applied to all routes** via `withSuspense()` wrapper in router.

### 3. Global Error Handler (Frontend)

**File:** `src/main.tsx`

Catches unhandled chunk errors globally and reloads the page:
```typescript
setupChunkErrorHandler();
```

This is a safety net for errors that escape the retry logic and error boundaries.

### 4. Cache Busting (Build Configuration)

**File:** `vite.config.ts`

Explicit hash-based filenames for all assets:
```typescript
output: {
  entryFileNames: 'assets/[name]-[hash].js',
  chunkFileNames: 'assets/[name]-[hash].js',
  assetFileNames: 'assets/[name]-[hash].[ext]',
}
```

This ensures every build creates unique filenames, allowing old and new versions to coexist temporarily.

### 5. HTML Cache Prevention (Frontend)

**File:** `index.html`

Meta tags prevent HTML caching:
```html
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
<meta http-equiv="Pragma" content="no-cache" />
<meta http-equiv="Expires" content="0" />
```

This ensures browsers always fetch fresh HTML with correct chunk references.

### 6. Server Cache Headers (Backend)

**File:** `backend/main.py`

Both root route and SPA middleware add cache prevention headers:
```python
response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
response.headers["Pragma"] = "no-cache"
response.headers["Expires"] = "0"
```

This works alongside frontend meta tags to prevent HTML caching.

## Defense in Depth Strategy

This solution implements **multiple layers of protection**:

| Layer | What It Does | Fallback If It Fails |
|-------|--------------|----------------------|
| 1. Cache Prevention | Prevents HTML caching | Retry logic catches stale chunks |
| 2. Chunk Retry | Automatically retries failed imports | Error boundary catches failures |
| 3. Error Boundary | Shows friendly error UI | Global handler reloads page |
| 4. Global Handler | Last resort: reload page | User sees error, can manually reload |

## Deployment Checklist

### Pre-Deployment

- [ ] Build frontend: `cd operator-dashboard && npm run build`
- [ ] Verify build output in `operator-dashboard/dist/`
- [ ] Check that chunk hashes are different from previous build
- [ ] Test locally with `npm run preview`

### Deployment (Render)

- [ ] Commit and push changes to repository
- [ ] Monitor Render build logs for frontend build completion
- [ ] Wait for deployment to complete
- [ ] Test deployed version immediately

### Post-Deployment Testing

- [ ] Open production URL in fresh browser session
- [ ] Navigate to all major routes
- [ ] Open in one tab, deploy new version, navigate in first tab (should auto-reload)
- [ ] Check browser console for errors
- [ ] Test in multiple browsers (Chrome, Firefox, Safari)

## Monitoring

### What to Watch For

1. **Browser Console Errors**
   - Look for chunk loading errors
   - Check if retry logic is working
   - Monitor auto-reload events

2. **User Reports**
   - "Page suddenly reloaded" = retry/handler working correctly
   - "Stuck on error screen" = possible issue with reload logic
   - "White screen" = error boundary not catching something

### Debugging

**If users still report chunk errors:**

1. Check if HTML cache prevention headers are being sent:
   ```bash
   curl -I https://your-domain.com/
   # Should see: Cache-Control: no-cache, no-store, must-revalidate
   ```

2. Check if chunks exist on server:
   ```bash
   curl -I https://your-domain.com/assets/Component-[hash].js
   # Should return 200 OK
   ```

3. Check browser DevTools Network tab:
   - Look for 404s on chunk files
   - Verify HTML file is not cached (Status: 200, not 304)

4. Test chunk retry in development:
   ```typescript
   // Temporarily force a chunk error
   const Component = lazy(() => Promise.reject(new Error('Test chunk error')));
   // Should see retry attempts in console, then reload
   ```

## Best Practices

### For Developers

1. **Always use `lazyWithRetry()`** for code splitting:
   ```typescript
   // ✅ Good
   const Page = lazyWithRetry(() => import('./pages/Page'));

   // ❌ Bad
   const Page = lazy(() => import('./pages/Page'));
   ```

2. **Wrap new route components** in ErrorBoundary (already done in router)

3. **Test deployments** with simulated stale cache:
   - Open app, deploy new version, navigate

4. **Monitor build output** for chunk hash changes

### For Deployments

1. **Deploy during low-traffic periods** when possible
2. **Monitor immediately after deployment** for 5-10 minutes
3. **Keep previous build artifacts** for quick rollback if needed
4. **Communicate deployments** to active users when critical

### For Production Server

1. **Configure CDN/proxy** to respect cache headers
2. **Set proper cache duration** for `/assets/*` (1 year is safe due to hashes)
3. **Never cache** HTML files (index.html and SPA routes)

## Rollback Procedure

If a deployment causes critical issues:

1. **Immediate:** Revert git commit and redeploy
   ```bash
   git revert HEAD
   git push
   # Render will auto-deploy
   ```

2. **Alternative:** Use Render's rollback feature in dashboard
   - Go to deployment history
   - Click "Rollback to this version"

3. **Notify users** to hard refresh (Ctrl+Shift+R)

## Architecture Decisions

### Why Multiple Layers?

Different browsers and CDNs handle caching differently. Multiple layers ensure:
- Chrome/Firefox/Safari all work correctly
- CDNs respect our no-cache policy
- Users behind corporate proxies get fresh content
- Race conditions during deployment are handled

### Why Auto-Reload Instead of Notification?

**Auto-reload** is better than showing "New version available, click to reload" because:
- Users don't need to take action
- Prevents confusion about what to do
- Chunk errors are transparent to users
- Failed reloads will show error boundary

### Why Exponential Backoff?

Immediate retry might fail if:
- CDN is still propagating new files
- Network had temporary issue
- Browser cache is clearing

Exponential backoff gives time for issues to resolve naturally.

## Technical Reference

### Chunk Loading Flow

```
User navigates → React Router loads route
                          ↓
              lazyWithRetry imports chunk
                          ↓
         ┌─────────────────────────────┐
         │ Try to fetch chunk          │
         └─────────────────────────────┘
                    ↓
         ┌──────────┴──────────┐
         │                     │
    Success ✓              Failure ✗
         │                     │
    Render component      Retry logic
                               │
                          ┌────┴─────┐
                          │          │
                    Success ✓    Final Failure ✗
                          │          │
                    Render component  │
                                      ↓
                               Global handler
                                      │
                               Reload page
                                      │
                          ┌────────────┴────────────┐
                          │                         │
                   Works ✓                    Still fails ✗
                          │                         │
                   User continues            Error boundary
                                                     │
                                            Friendly error screen
```

### Error Detection Logic

Chunk loading errors are identified by these patterns:
- `Failed to fetch dynamically imported module`
- `Importing a module script failed`
- `error loading dynamically imported module`
- `ChunkLoadError`
- `Failed to fetch` (generic network error)
- `NetworkError`

## Maintenance

### Regular Tasks

**Weekly:**
- Check monitoring for chunk error patterns
- Review deployment logs for build failures

**Monthly:**
- Test deployment process in staging
- Update dependencies and rebuild
- Review error logs for new error patterns

**Quarterly:**
- Review and update cache policies
- Test rollback procedures
- Update this documentation

## Support

### Common User Issues

**"Page keeps reloading"**
- Likely: Retry logic working, but chunks still failing
- Action: Check server deployment completed successfully
- Solution: Wait 1-2 minutes for CDN propagation

**"Stuck on error screen"**
- Likely: Error boundary caught error, auto-reload failed
- Action: Check browser console for errors
- Solution: Ask user to hard refresh (Ctrl+Shift+R)

**"White/blank screen"**
- Likely: JavaScript error before error boundary mounted
- Action: Check recent code changes
- Solution: Rollback deployment

## Related Documentation

- [Vite Build Configuration](https://vitejs.dev/config/build-options.html)
- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [React Router Error Handling](https://reactrouter.com/en/main/route/error-element)
- [HTTP Caching Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)

## Changelog

### 2025-12-22 - Initial Implementation
- Added automatic chunk retry utility
- Implemented ErrorBoundary component
- Added global chunk error handler
- Configured cache busting in Vite
- Added HTML cache prevention headers
- Updated backend to prevent HTML caching
- Created this documentation
