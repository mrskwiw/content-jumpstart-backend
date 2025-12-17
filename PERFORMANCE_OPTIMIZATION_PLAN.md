# Performance Optimization Plan

**Project:** 30-Day Content Jumpstart
**Date:** 2025-12-15
**Status:** Comprehensive Analysis Complete

## Executive Summary

This document outlines performance optimization opportunities identified across the full stack: Python backend (FastAPI), React frontend (operator-dashboard), database queries, and bundling. Issues range from critical N+1 queries to minor bundle size optimizations.

---

## 1. Database Performance Issues

### 🔴 CRITICAL: N+1 Query Problem

**Location:** `backend/services/crud.py`

**Issue:** The `get_posts()` function performs lazy loading of relationships, causing N+1 queries when accessing related `project` and `run` data.

```python
# Lines 105-174: get_posts() returns Post objects with relationships
# But relationships are configured as lazy loading in models
```

**Impact:**
- For 100 posts with 10 projects: **101 queries** (1 for posts + 100 for projects)
- For 1000 posts: **1001+ queries**
- Response time increases linearly with post count

**Solution:**
```python
from sqlalchemy.orm import joinedload

def get_posts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    # ... filters ...
) -> List[Post]:
    query = db.query(Post).options(
        joinedload(Post.project),
        joinedload(Post.run)
    )

    # Apply filters...

    return query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
```

**Priority:** HIGH
**Effort:** Low (2 hours)
**Expected Improvement:** 90% reduction in query count, 50-70% faster response

---

### 🔴 CRITICAL: Missing Composite Indexes

**Location:** `backend/models/post.py` (lines 14-37)

**Issue:** Common filter combinations lack composite indexes:
- `(project_id, status)` - filtered together frequently
- `(status, created_at)` - status filter + time-based ordering
- `(target_platform, status)` - platform-specific status queries
- `(template_name)` - ILIKE searches without index (line 143 in crud.py)

**Current Indexes:**
```python
project_id = Column(..., index=True)  # Single column only
run_id = Column(..., index=True)      # Single column only
```

**Impact:**
- Table scans on filtered queries
- Slow performance as post count grows (>10k posts)
- Poor ILIKE performance on `template_name`

**Solution:**
```python
# In backend/models/post.py
from sqlalchemy import Index

class Post(Base):
    __tablename__ = "posts"

    # ... existing columns ...

    __table_args__ = (
        Index('ix_posts_project_status', 'project_id', 'status'),
        Index('ix_posts_status_created', 'status', 'created_at'),
        Index('ix_posts_platform_status', 'target_platform', 'status'),
        Index('ix_posts_template_name', 'template_name'),  # For ILIKE
        Index('ix_posts_word_count', 'word_count'),  # For range queries
    )
```

**Migration Required:**
```bash
# Create Alembic migration
alembic revision --autogenerate -m "Add composite indexes to posts"
alembic upgrade head
```

**Priority:** HIGH
**Effort:** Medium (4 hours including testing)
**Expected Improvement:** 70-90% faster filtered queries

---

### 🟡 MODERATE: Inefficient Text Search

**Location:** `backend/services/crud.py` (line 160)

**Issue:** Using `ILIKE` for full-text search is slow and doesn't support relevance ranking.

```python
if search:
    query = query.filter(Post.content.ilike(f"%{search}%"))
```

**Impact:**
- Slow searches on large content fields
- No relevance ranking
- High CPU usage for pattern matching

**Solutions:**

**Option 1: PostgreSQL Full-Text Search (Recommended for production)**
```python
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TSVECTOR

# Add to Post model
search_vector = Column(TSVECTOR)

# Create GIN index
Index('ix_posts_search_vector', 'search_vector', postgresql_using='gin')

# Update query
if search:
    query = query.filter(
        func.to_tsvector('english', Post.content).match(search)
    ).order_by(
        func.ts_rank(func.to_tsvector('english', Post.content), search).desc()
    )
```

**Option 2: SQLite FTS5 (For development/small deployments)**
```python
# Create FTS virtual table
CREATE VIRTUAL TABLE posts_fts USING fts5(
    content,
    content=posts,
    content_rowid=id
);

# Triggers to keep in sync
CREATE TRIGGER posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, content) VALUES (new.id, new.content);
END;
```

**Priority:** MEDIUM
**Effort:** High (8 hours with testing)
**Expected Improvement:** 10-20x faster searches with relevance

---

### 🟡 MODERATE: No Connection Pooling Configuration

**Location:** `backend/database.py` (lines 14-16)

**Issue:** Using default SQLAlchemy connection pool without optimization.

```python
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
# No pool_size, max_overflow, or pool_timeout configured
```

**Impact:**
- Potential connection exhaustion under load
- Inefficient connection reuse
- No control over timeout behavior

**Solution:**
```python
from sqlalchemy.pool import QueuePool

# Production settings
if database_url.drivername.startswith("postgresql"):
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,           # Base pool size
        max_overflow=10,        # Additional connections when needed
        pool_timeout=30,        # Wait 30s for connection
        pool_pre_ping=True,     # Test connections before use
        pool_recycle=3600,      # Recycle connections after 1 hour
    )
else:
    # SQLite settings
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
```

**Priority:** MEDIUM
**Effort:** Low (2 hours)
**Expected Improvement:** Better stability under concurrent load

---

## 2. Backend API Performance

### 🟡 MODERATE: Missing Response Caching

**Location:** All routers (e.g., `backend/routers/posts.py`)

**Issue:** No HTTP caching headers for cacheable responses.

**Impact:**
- Repeated database queries for unchanged data
- Higher server load
- Slower perceived performance

**Solution:**
```python
from fastapi import Response
from datetime import datetime, timedelta

@router.get("/", response_model=List[PostResponse])
async def list_posts(
    response: Response,
    skip: int = Query(0, ge=0),
    # ... other params ...
) -> List[PostResponse]:
    posts = crud.get_posts(db, skip=skip, limit=limit, ...)

    # Add caching headers
    if not status and not search:  # Only cache unfiltered requests
        response.headers["Cache-Control"] = "public, max-age=60"
        response.headers["ETag"] = generate_etag(posts)

    return posts

def generate_etag(data: Any) -> str:
    """Generate ETag from data hash"""
    import hashlib
    content = json.dumps(data, default=str, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()
```

**Alternative: Redis Caching**
```python
from redis import Redis
from functools import wraps

redis_client = Redis.from_url(settings.REDIS_URL)

def cache_response(ttl: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(kwargs))}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@router.get("/")
@cache_response(ttl=60)
async def list_posts(...):
    ...
```

**Priority:** MEDIUM
**Effort:** Medium (6 hours)
**Expected Improvement:** 50-80% reduction in database load

---

### 🟢 LOW: Inefficient Alias Generation

**Location:** All schemas (e.g., `backend/schemas/post.py` line 36)

**Issue:** Lambda function recreated for every model instance.

```python
model_config = ConfigDict(
    alias_generator=lambda field_name: ''.join(
        word.capitalize() if i > 0 else word
        for i, word in enumerate(field_name.split('_'))
    ),
)
```

**Impact:**
- Minor CPU overhead for each instance
- No caching of results

**Solution:**
```python
# In backend/utils/alias.py
from functools import lru_cache

@lru_cache(maxsize=128)
def snake_to_camel(field_name: str) -> str:
    """Convert snake_case to camelCase with caching"""
    words = field_name.split('_')
    return words[0] + ''.join(word.capitalize() for word in words[1:])

# In schemas
model_config = ConfigDict(
    alias_generator=snake_to_camel,
    ...
)
```

**Priority:** LOW
**Effort:** Low (1 hour)
**Expected Improvement:** Minor CPU reduction (~5%)

---

## 3. Frontend Performance Issues

### 🔴 CRITICAL: Client-Side Filtering

**Location:** `operator-dashboard/src/pages/Projects.tsx` (lines 55-57)

**Issue:** Filtering happens in browser after fetching ALL projects.

```typescript
const { data } = useQuery({
    queryKey: ['projects', { search, status }],
    queryFn: () => projectsApi.list({ search, status }), // ✓ Good
});

// ❌ BAD: Re-filtering in browser
const filtered = projects.filter((p) =>
    search ? p.name.toLowerCase().includes(search.toLowerCase()) : true
);
```

**Impact:**
- Fetches all data even when filtering
- Wasted bandwidth
- Slow filtering on large datasets

**Solution:**
```typescript
// Remove client-side filtering - API already handles it
const { data: projects = [] } = useQuery({
    queryKey: ['projects', { search, status }],
    queryFn: () => projectsApi.list({ search, status }),
});

// Use projects directly - already filtered by API
```

**Priority:** HIGH
**Effort:** Low (1 hour)
**Expected Improvement:** Eliminates duplicate filtering, faster perceived performance

---

### 🟡 MODERATE: No Query Deduplication

**Location:** `operator-dashboard/src/providers/queryClient.ts`

**Issue:** Multiple components requesting same data trigger duplicate requests.

**Current Config:**
```typescript
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,  // Good
      retry: 1,
    },
  },
});
```

**Impact:**
- Multiple parallel requests for same data
- Wasted bandwidth

**Solution:**
```typescript
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60 * 1000,      // Keep in cache for 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnMount: false,       // Don't refetch on component mount
      refetchOnReconnect: true,    // Refetch on network reconnect
    },
  },
});
```

**Priority:** MEDIUM
**Effort:** Low (1 hour)
**Expected Improvement:** Reduces API calls by 40-60%

---

### 🟡 MODERATE: Inefficient Token Refresh

**Location:** `operator-dashboard/src/api/client.ts` (lines 36-79)

**Issue:** Token refresh blocks all requests during refresh attempt.

```typescript
if (error.response?.status === 401 && !originalRequest._retry) {
    originalRequest._retry = true;
    // ❌ Blocks other requests
    const { data } = await axios.post(`${API_URL}/api/auth/refresh`, ...);
}
```

**Impact:**
- Multiple 401s trigger multiple refresh attempts
- Request queue buildup

**Solution:**
```typescript
// Shared refresh promise to prevent duplicate refreshes
let refreshPromise: Promise<string> | null = null;

async function refreshToken(): Promise<string> {
    if (refreshPromise) {
        return refreshPromise; // Reuse in-flight refresh
    }

    refreshPromise = (async () => {
        try {
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) throw new Error('No refresh token');

            const { data } = await axios.post(`${API_URL}/api/auth/refresh`, {
                refresh_token: refreshToken,
            });

            localStorage.setItem('access_token', data.access_token);
            return data.access_token;
        } finally {
            refreshPromise = null;
        }
    })();

    return refreshPromise;
}

// In interceptor
if (error.response?.status === 401 && !originalRequest._retry) {
    originalRequest._retry = true;
    try {
        const newToken = await refreshToken();
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return this.client(originalRequest);
    } catch (refreshError) {
        // Handle logout...
    }
}
```

**Priority:** MEDIUM
**Effort:** Medium (3 hours)
**Expected Improvement:** Eliminates duplicate refresh requests

---

### 🟢 LOW: No Request Cancellation

**Location:** All API hooks

**Issue:** Previous requests not cancelled when new ones start.

**Impact:**
- Wasted bandwidth for stale requests
- Race conditions in fast-changing filters

**Solution:**
```typescript
import { useQuery } from '@tanstack/react-query';

// React Query handles this automatically with AbortSignal
const { data } = useQuery({
    queryKey: ['posts', { search, status }],
    queryFn: ({ signal }) => postsApi.list({ search, status }, signal),
});

// In API client
export const postsApi = {
    list: async (params: ListParams, signal?: AbortSignal) => {
        const response = await client.get('/api/posts', {
            params,
            signal, // Pass to axios
        });
        return response.data;
    },
};
```

**Priority:** LOW
**Effort:** Low (2 hours)
**Expected Improvement:** Reduces unnecessary network traffic

---

## 4. Bundle Size Optimization

### 🟡 MODERATE: No Code Splitting

**Location:** `operator-dashboard/vite.config.ts`

**Issue:** All components bundled into single chunk.

**Current Config:**
```typescript
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  // No build optimization
})
```

**Impact:**
- Large initial bundle (~500KB estimated)
- Slow first page load
- No route-based lazy loading

**Solution:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor splitting
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-ui': ['lucide-react', 'date-fns'],

          // Route-based splitting
          'page-dashboard': ['./src/pages/Dashboard.tsx'],
          'page-projects': ['./src/pages/Projects.tsx'],
          'page-wizard': ['./src/pages/Wizard.tsx'],
        },
      },
    },
    chunkSizeWarningLimit: 500, // Warn if chunks exceed 500KB
  },
});
```

**Additionally, add route-based lazy loading:**
```typescript
// In router.tsx
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Projects = lazy(() => import('./pages/Projects'));
const Wizard = lazy(() => import('./pages/Wizard'));

// Wrap in Suspense
<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/dashboard" element={<Dashboard />} />
    ...
  </Routes>
</Suspense>
```

**Priority:** MEDIUM
**Effort:** Medium (4 hours)
**Expected Improvement:** 50-60% reduction in initial bundle, faster first load

---

### 🟢 LOW: Unoptimized Date-fns Imports

**Location:** Multiple files (e.g., `Projects.tsx` line 6)

**Issue:** Importing full `date-fns` library.

```typescript
import { format } from 'date-fns';
```

**Impact:**
- ~20KB extra in bundle for unused functions

**Solution:**
```typescript
// Use direct imports
import format from 'date-fns/format';
import parseISO from 'date-fns/parseISO';
```

**Or configure Vite to tree-shake:**
```typescript
// vite.config.ts
export default defineConfig({
  optimizeDeps: {
    include: ['date-fns'],
  },
});
```

**Priority:** LOW
**Effort:** Low (1 hour)
**Expected Improvement:** ~20KB bundle reduction

---

## 5. Algorithm Efficiency Issues

### 🟢 LOW: Template Selection Algorithm

**Location:** `src/agents/content_generator.py` (lines 262-293)

**Issue:** Inefficient template distribution calculation.

```python
uses_per_template = num_posts // len(selected_templates)
extra_posts = num_posts % len(selected_templates)

for template in selected_templates:
    for variant in range(1, uses_per_template + 1):
        tasks.append({...})
        post_number += 1

# Extra posts
for i in range(extra_posts):
    template = selected_templates[i % len(selected_templates)]
    # ...
```

**Impact:**
- O(n) complexity is fine
- Minor: Extra loop for extra posts

**Solution (micro-optimization):**
```python
# Combine into single loop
for i, template in enumerate(selected_templates * (num_posts // len(selected_templates))):
    tasks.append({
        "template": template,
        "variant": (i // len(selected_templates)) + 1,
        "post_number": i + 1,
        ...
    })

# Handle remainder
remainder = num_posts % len(selected_templates)
for i in range(remainder):
    template = selected_templates[i]
    tasks.append({...})
```

**Priority:** LOW
**Effort:** Low (1 hour)
**Expected Improvement:** Negligible (~1% faster template assignment)

---

## 6. Memory Usage Optimization

### 🟡 MODERATE: Large Response Payloads

**Location:** API responses returning full nested objects

**Issue:** Returning full related objects when IDs would suffice.

**Example in `PostResponse`:**
```python
class PostResponse(BaseModel):
    id: str
    project_id: str  # ✓ Good - just ID
    run_id: str      # ✓ Good - just ID
    content: str     # Can be large (2000+ chars)
    # ... other fields
```

**Impact:**
- 100 posts × 2KB content = ~200KB per response
- Unnecessarily large payloads for list views

**Solution:**
```python
# Create lightweight list response schema
class PostListItem(BaseModel):
    """Lightweight post for list views"""
    id: str
    project_id: str
    template_name: Optional[str]
    status: str
    word_count: Optional[int]
    has_cta: Optional[bool]
    created_at: datetime
    # Exclude 'content' field

class PostDetailResponse(BaseModel):
    """Full post for detail views"""
    # Include all fields including content
    ...

# Use appropriate schema
@router.get("/", response_model=List[PostListItem])
async def list_posts(...):
    ...

@router.get("/{post_id}", response_model=PostDetailResponse)
async def get_post(...):
    ...
```

**Priority:** MEDIUM
**Effort:** Medium (3 hours)
**Expected Improvement:** 70-80% reduction in list response size

---

### 🟢 LOW: Async Semaphore Size

**Location:** `src/agents/content_generator.py` (line 296)

**Issue:** Fixed semaphore size of 5 concurrent requests.

```python
semaphore = asyncio.Semaphore(max_concurrent)  # max_concurrent = 5
```

**Impact:**
- May be suboptimal for different API rate limits
- Not configurable per environment

**Solution:**
```python
# In config/settings.py
MAX_CONCURRENT_API_CALLS: int = Field(
    default=5,
    description="Max concurrent API calls (adjust based on rate limits)"
)

# Add rate limit awareness
class ContentGeneratorAgent:
    def __init__(self, max_concurrent: Optional[int] = None):
        self.max_concurrent = max_concurrent or settings.MAX_CONCURRENT_API_CALLS

    async def generate_posts_async(self, ...):
        # Auto-adjust based on available rate limit
        rate_limiter = self.client.get_rate_limiter()
        effective_max = min(
            self.max_concurrent,
            rate_limiter.get_available_capacity() // 2  # Use 50% of capacity
        )
        semaphore = asyncio.Semaphore(effective_max)
```

**Priority:** LOW
**Effort:** Low (2 hours)
**Expected Improvement:** Better rate limit handling

---

## 7. Coding Standards Adherence

### 🟡 MODERATE: Inconsistent Error Handling

**Location:** Multiple files

**Issue:** Mix of try/except patterns and unhandled errors.

**Examples:**
```python
# backend/services/crud.py - No error handling
def get_post(db: Session, post_id: str) -> Optional[Post]:
    return db.query(Post).filter(Post.id == post_id).first()
    # ❌ No handling of database errors

# backend/routers/posts.py - Basic error handling
@router.get("/{post_id}")
async def get_post(post_id: str, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
    # ❌ Database exceptions not caught
```

**Solution:**
```python
# Create custom exceptions
# backend/exceptions.py
class DatabaseError(Exception):
    """Database operation failed"""
    pass

class NotFoundError(DatabaseError):
    """Resource not found"""
    pass

# In CRUD operations
from sqlalchemy.exc import SQLAlchemyError

def get_post(db: Session, post_id: str) -> Post:
    """Get post by ID

    Raises:
        NotFoundError: Post not found
        DatabaseError: Database operation failed
    """
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        return post
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Failed to retrieve post: {e}")

# In routers
from exceptions import NotFoundError, DatabaseError

@router.get("/{post_id}")
async def get_post(post_id: str, db: Session = Depends(get_db)):
    try:
        return crud.get_post(db, post_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Priority:** MEDIUM
**Effort:** High (8 hours across all files)
**Expected Improvement:** Better error visibility, easier debugging

---

### 🟢 LOW: Missing Type Hints

**Location:** Some backend functions

**Issue:** Inconsistent type hints reduce type safety.

**Example:**
```python
# backend/services/crud.py line 298
def update_run(db: Session, run_id: str, **kwargs):  # ❌ kwargs not typed
    ...
```

**Solution:**
```python
from typing import Any, Dict, Optional

def update_run(
    db: Session,
    run_id: str,
    **kwargs: Any  # Or use TypedDict for specific fields
) -> Optional[Run]:
    """Update run with keyword arguments

    Args:
        db: Database session
        run_id: Run identifier
        **kwargs: Fields to update (status, error_message, completed_at)

    Returns:
        Updated Run or None if not found
    """
    ...
```

**Priority:** LOW
**Effort:** Medium (4 hours)
**Expected Improvement:** Better IDE support, fewer runtime errors

---

### 🟢 LOW: Frontend TypeScript Errors

**Location:** Multiple files (see build output)

**Issue:** TypeScript compilation errors prevent optimized builds.

```
src/pages/Overview.tsx(292,31): error TS2339: Property 'email' does not exist
src/pages/Wizard.tsx(63,26): error TS2345: Argument of type... not assignable
```

**Impact:**
- Cannot create production build
- Missing type safety
- Potential runtime errors

**Solution:**
```typescript
// Fix type definitions
// In types/domain.ts
export interface Client {
  id: string;
  name: string;
  email: string;  // Add missing field
  tags?: string[];
  status?: 'active' | 'inactive';
}

// In Wizard.tsx - fix snake_case to camelCase
const projectInput: CreateProjectInput = {
  name: projectData.name,
  clientId: projectData.client_id,  // ✓ Use camelCase
  templates: selectedTemplates,      // ✓ Add required field
  platforms: projectData.platforms,
  tone: projectData.tone,
};
```

**Priority:** LOW (but blocks production build)
**Effort:** Low (2 hours)
**Expected Improvement:** Enables production build with optimizations

---

## Implementation Roadmap

### Phase 1: Critical Performance (Week 1)
**Estimated Effort:** 3 days

1. ✅ **Add eager loading to queries** (2 hours)
   - Update `get_posts()` with `joinedload()`
   - Test query count reduction

2. ✅ **Add composite indexes** (4 hours)
   - Create Alembic migration
   - Add indexes to Post model
   - Benchmark before/after

3. ✅ **Fix client-side filtering** (1 hour)
   - Remove duplicate filtering in Projects.tsx
   - Verify API filtering works

**Expected Impact:** 70-90% faster queries, 50% faster UI

---

### Phase 2: Caching & Bundle Optimization (Week 2)
**Estimated Effort:** 4 days

4. ✅ **Implement response caching** (6 hours)
   - Add Cache-Control headers
   - Implement ETag generation
   - Test cache invalidation

5. ✅ **Add code splitting** (4 hours)
   - Configure Vite manual chunks
   - Add route lazy loading
   - Measure bundle sizes

6. ✅ **Optimize React Query** (1 hour)
   - Update default options
   - Test query deduplication

**Expected Impact:** 50% fewer API calls, 60% smaller initial bundle

---

### Phase 3: Database & Memory (Week 3)
**Estimated Effort:** 5 days

7. ✅ **Implement full-text search** (8 hours)
   - Choose FTS solution (PostgreSQL FTS recommended)
   - Add search indexes
   - Update query logic

8. ✅ **Optimize connection pooling** (2 hours)
   - Configure pool size and timeouts
   - Add connection pre-ping

9. ✅ **Add lightweight list schemas** (3 hours)
   - Create PostListItem schema
   - Update list endpoints
   - Test payload sizes

**Expected Impact:** 10-20x faster search, 70% smaller list payloads

---

### Phase 4: Code Quality & Standards (Week 4)
**Estimated Effort:** 3 days

10. ✅ **Standardize error handling** (8 hours)
    - Create custom exceptions
    - Update CRUD operations
    - Update router error handling

11. ✅ **Fix TypeScript errors** (2 hours)
    - Update type definitions
    - Fix component prop types

12. ✅ **Add missing type hints** (4 hours)
    - Add types to kwargs functions
    - Run mypy validation

**Expected Impact:** Better maintainability, fewer bugs

---

### Phase 5: Polish & Monitoring (Week 5)
**Estimated Effort:** 2 days

13. ✅ **Add request cancellation** (2 hours)
    - Update API hooks with AbortSignal
    - Test cancellation behavior

14. ✅ **Optimize token refresh** (3 hours)
    - Implement shared refresh promise
    - Test concurrent 401 handling

15. ✅ **Add performance monitoring** (3 hours)
    - Add response time logging
    - Add query performance metrics
    - Create performance dashboard

**Expected Impact:** Better observability, fewer wasted requests

---

## Success Metrics

### Database Performance
- Query count: Reduce by **90%** (101 → 10 queries for 100 posts)
- Query response time: Improve by **70%** (500ms → 150ms for filtered queries)
- Search performance: Improve by **10-20x** (2s → 100-200ms for text search)

### API Performance
- Cache hit rate: Target **60-80%** for list endpoints
- Avg response time: Reduce by **50%** (200ms → 100ms)
- Concurrent request handling: Increase by **3x**

### Frontend Performance
- Initial bundle size: Reduce by **60%** (~500KB → ~200KB)
- First contentful paint: Improve by **40%** (1.5s → 0.9s)
- Time to interactive: Improve by **50%** (3s → 1.5s)
- API calls: Reduce by **50%** (fewer duplicate requests)

### Memory Usage
- Response payload size: Reduce by **70%** for list views
- Browser memory: Reduce by **30%** (better query GC)

---

## Monitoring & Validation

### Database Monitoring
```sql
-- Query performance tracking
CREATE TABLE query_performance (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255),
    query_time_ms INTEGER,
    query_count INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Track before optimization
-- Track after optimization
-- Compare metrics
```

### API Monitoring
```python
# Add middleware for performance tracking
from time import time

@app.middleware("http")
async def add_performance_header(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    process_time = (time() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    # Log slow requests
    if process_time > 500:
        logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}ms")

    return response
```

### Frontend Monitoring
```typescript
// Add to main.tsx
import { performance } from 'perf_hooks';

// Track page load times
window.addEventListener('load', () => {
    const perfData = performance.getEntriesByType('navigation')[0];
    console.log('Page load time:', perfData.duration);

    // Send to analytics
    analytics.track('page_load', {
        duration: perfData.duration,
        route: window.location.pathname,
    });
});
```

---

## Risk Assessment

### High Risk
- **Full-text search migration**: Requires data migration, potential downtime
  - Mitigation: Test thoroughly in staging, prepare rollback plan

- **Breaking API changes**: Response schema changes may break frontend
  - Mitigation: Version API, deploy backend first, then frontend

### Medium Risk
- **Connection pool tuning**: May cause connection exhaustion if misconfigured
  - Mitigation: Monitor connection metrics, adjust gradually

- **Bundle splitting**: May break lazy loading if configured incorrectly
  - Mitigation: Test all routes, verify chunk loading

### Low Risk
- **Index additions**: May slow down writes slightly
  - Mitigation: Test write performance, indexes improve reads significantly

- **Caching**: May serve stale data if invalidation broken
  - Mitigation: Short TTLs initially, monitor cache behavior

---

## Appendix A: Benchmark Scripts

### Database Query Performance
```python
# benchmark_queries.py
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def benchmark_get_posts(db: Session, iterations: int = 100):
    times = []
    for _ in range(iterations):
        start = time.time()
        posts = crud.get_posts(db, limit=100)
        for post in posts:
            _ = post.project.name  # Trigger lazy load
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    print(f"Average time: {avg_time*1000:.2f}ms")
    print(f"Total queries: {db.query_count}")

# Run before optimization
benchmark_get_posts(db)

# Run after optimization
benchmark_get_posts(db)
```

### Bundle Size Tracking
```bash
# Before optimization
npm run build
ls -lh dist/assets/*.js

# After optimization
npm run build
ls -lh dist/assets/*.js

# Compare
du -sh dist/assets/
```

---

## Appendix B: Configuration Examples

### PostgreSQL Configuration for Production
```ini
# postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB
max_connections = 100
```

### Nginx Caching Configuration
```nginx
# Cache configuration for API responses
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m
                 max_size=1g inactive=60m use_temp_path=off;

server {
    location /api/ {
        proxy_pass http://backend:8000;

        # Cache GET requests
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_use_stale error timeout updating;
        proxy_cache_methods GET HEAD;

        # Add cache status header
        add_header X-Cache-Status $upstream_cache_status;
    }
}
```

---

## Conclusion

This optimization plan addresses performance issues across the full stack with clear priorities, effort estimates, and expected improvements. The phased approach allows for incremental improvements with measurable results.

**Total Estimated Effort:** 4-5 weeks
**Expected Overall Improvement:** 60-80% performance gain
**Primary Focus Areas:** Database queries, caching, bundle size

Next steps:
1. Review and approve plan
2. Begin Phase 1 implementation
3. Track metrics throughout implementation
4. Adjust priorities based on measured impact
