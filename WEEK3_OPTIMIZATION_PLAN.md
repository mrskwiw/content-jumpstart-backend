# Week 3 Performance Optimization Plan

**Date:** 2025-12-15
**Status:** 🚧 In Progress
**Focus:** Database connection pooling, query optimization, pagination, and backend performance

---

## Overview

Week 3 builds on the HTTP caching and code splitting from Week 2 by optimizing the database layer and backend infrastructure. This week focuses on:

1. **Database connection pooling** - Optimize connection management
2. **Query result caching** - Add server-side caching for expensive queries
3. **Pagination optimization** - Improve large result set handling
4. **Query profiling** - Identify and fix slow queries
5. **Background tasks** - Optimize async operations

---

## Week 3 Tasks

### Task 1: Database Connection Pooling ⏳

**Goal**: Optimize SQLAlchemy connection pool settings for production workload

**Current State**: Using default connection pool settings
- Pool size: 5 connections (default)
- Max overflow: 10 (default)
- Pool recycle: None
- Pool pre-ping: Disabled

**Target State**: Production-optimized connection pool
- Pool size: 20 connections
- Max overflow: 40 connections
- Pool recycle: 3600 seconds (1 hour)
- Pool pre-ping: Enabled (detect stale connections)
- Echo pool: Disabled in production

**Implementation Steps**:
1. Read current `backend/database.py` configuration
2. Add connection pool settings to `backend/config.py`
3. Update `create_engine()` with optimized pool parameters
4. Add connection pool monitoring
5. Test connection pool behavior under load

**Files to Modify**:
- `backend/database.py` - Engine configuration
- `backend/config.py` - Pool settings as environment variables

**Expected Impact**:
- Faster query execution (reuse connections)
- Better handling of concurrent requests
- Reduced database connection overhead
- Improved application stability under load

---

### Task 2: Server-Side Query Caching ⏳

**Goal**: Add server-side caching layer for expensive queries using cachetools

**Caching Strategy**:
- Use in-memory LRU cache (cachetools)
- Cache expensive aggregations and counts
- Cache client/project lists for short periods
- Invalidate cache on mutations

**Queries to Cache**:
1. `GET /api/posts` with filters - 5 minute TTL
2. `GET /api/projects` with filters - 5 minute TTL
3. `GET /api/clients` - 10 minute TTL
4. Project/client counts - 5 minute TTL
5. Dashboard statistics - 5 minute TTL

**Implementation Steps**:
1. Add `cachetools` dependency to requirements.txt
2. Create `backend/utils/query_cache.py` with cache decorator
3. Apply cache decorator to expensive CRUD functions
4. Add cache invalidation on mutations
5. Add cache statistics endpoint for monitoring

**Files to Create**:
- `backend/utils/query_cache.py` - Caching decorator and utilities

**Files to Modify**:
- `backend/services/crud.py` - Add caching to expensive queries
- `backend/requirements.txt` - Add cachetools

**Expected Impact**:
- 70-90% faster response times for repeated queries
- Reduced database load (fewer queries)
- Lower CPU usage (cached results)
- Better scalability under concurrent load

---

### Task 3: Pagination Optimization ⏳

**Goal**: Optimize pagination for large result sets using keyset pagination

**Current State**: Using offset-based pagination
```python
query.offset(skip).limit(limit)
```

**Problem**: Slow for large offsets (page 100+ requires scanning all previous rows)

**Target State**: Hybrid pagination strategy
- Offset pagination for small offsets (< 1000 rows)
- Keyset (cursor) pagination for large offsets
- Add `cursor` parameter to API endpoints
- Return `next_cursor` in responses

**Implementation Steps**:
1. Create pagination utility in `backend/utils/pagination.py`
2. Add cursor-based pagination for posts and projects
3. Update API responses to include pagination metadata
4. Add pagination parameters to OpenAPI schema
5. Document pagination strategy

**Files to Create**:
- `backend/utils/pagination.py` - Pagination utilities

**Files to Modify**:
- `backend/services/crud.py` - Add cursor pagination methods
- `backend/routers/posts.py` - Support cursor parameter
- `backend/routers/projects.py` - Support cursor parameter
- `backend/schemas/*.py` - Add pagination response models

**Expected Impact**:
- Constant-time pagination (regardless of offset)
- Faster loading for large result sets
- Better user experience for deep pagination
- Reduced database CPU usage

---

### Task 4: Query Profiling and Optimization ⏳

**Goal**: Profile queries and optimize slow operations

**Profiling Strategy**:
1. Enable SQLAlchemy query logging
2. Add query timing middleware
3. Identify queries > 100ms
4. Optimize with indexes or query restructuring
5. Monitor query performance in production

**Implementation Steps**:
1. Create query profiling middleware in `backend/middleware/query_profiler.py`
2. Add slow query logging
3. Profile common queries (posts, projects, deliverables)
4. Add missing indexes based on profiling results
5. Create query performance report

**Files to Create**:
- `backend/middleware/query_profiler.py` - Query timing middleware
- `backend/scripts/profile_queries.py` - Query profiling script

**Files to Modify**:
- `backend/main.py` - Add profiling middleware
- `backend/models/*.py` - Add additional indexes if needed

**Expected Impact**:
- Identify and fix slow queries
- Reduce p95 response times by 50%+
- Better understanding of query patterns
- Data-driven optimization decisions

---

### Task 5: Background Task Optimization ⏳

**Goal**: Optimize async operations and background tasks

**Areas to Optimize**:
1. Bulk post generation (already async, but can optimize)
2. File uploads (async processing)
3. Email sending (move to background queue)
4. Analytics calculations (defer to background)

**Implementation Steps**:
1. Audit current background tasks
2. Add task queue (using FastAPI BackgroundTasks or Celery)
3. Move expensive operations to background
4. Add task status tracking
5. Implement task retry logic

**Files to Create**:
- `backend/tasks/background_tasks.py` - Background task definitions
- `backend/tasks/task_queue.py` - Task queue management

**Files to Modify**:
- `backend/routers/*.py` - Move expensive ops to background
- `backend/main.py` - Add background task configuration

**Expected Impact**:
- Faster API response times (non-blocking)
- Better user experience (immediate responses)
- Improved scalability (distribute work)
- More reliable task execution (retries)

---

## Week 3 Timeline

**Estimated Time**: 6-8 hours total

| Task | Estimated Time | Priority |
|------|---------------|----------|
| 1. Connection Pooling | 1 hour | High |
| 2. Query Caching | 2 hours | High |
| 3. Pagination | 2 hours | Medium |
| 4. Query Profiling | 2 hours | Medium |
| 5. Background Tasks | 1-2 hours | Low |

**Recommended Order**:
1. Start with Connection Pooling (quick win, foundation for rest)
2. Add Query Caching (biggest performance impact)
3. Implement Query Profiling (identify other bottlenecks)
4. Optimize Pagination (if profiling shows it's an issue)
5. Background Tasks (if time permits)

---

## Success Metrics

### Performance Targets

**Database**:
- Query response time p50: < 10ms
- Query response time p95: < 50ms
- Connection pool utilization: 60-80%
- Cache hit rate: > 70%

**API**:
- Response time p50: < 100ms
- Response time p95: < 300ms
- Throughput: 100+ req/sec
- Error rate: < 0.1%

**User Experience**:
- Page load time: < 1 second
- Pagination: Constant time regardless of offset
- Background operations: Non-blocking

---

## Monitoring and Testing

### Development Testing
- Load test with locust or wrk
- Profile queries with SQLAlchemy logging
- Monitor connection pool usage
- Verify cache hit rates

### Production Monitoring
- Add performance metrics endpoint
- Track query timing distributions
- Monitor connection pool metrics
- Alert on slow queries (> 100ms)

---

## Dependencies

**New Python Packages**:
```txt
cachetools==5.3.2  # In-memory caching
```

**Existing Packages** (no changes):
- SQLAlchemy - ORM and connection pooling
- FastAPI - Background tasks support
- PostgreSQL - Database

---

## Rollback Plan

If any optimization causes issues:

1. **Connection Pooling**: Revert to default pool settings in `database.py`
2. **Query Caching**: Remove cache decorators from `crud.py`
3. **Pagination**: Remove cursor parameter, keep offset pagination
4. **Query Profiling**: Disable profiling middleware in `main.py`
5. **Background Tasks**: Keep synchronous execution

Each change is isolated and can be rolled back independently.

---

## Next Steps

After Week 3 completion:
- **Week 4**: Frontend performance (React Query advanced patterns, virtual scrolling)
- **Week 5**: Infrastructure (Redis integration, load balancing)
- **Week 6**: Monitoring and observability (metrics, traces, alerts)

---

**Started**: 2025-12-15
**Target Completion**: 2025-12-15 (same day - 6-8 hours)
**Status**: 🚧 Task 1 in progress
