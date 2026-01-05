# Performance Baselines

**Version:** 1.0
**Last Updated:** 2025-12-29
**Benchmark Environment:** Production-equivalent (4 CPU, 16GB RAM, PostgreSQL)

This document establishes performance baselines for regression detection and capacity planning.

---

## API Endpoint Performance

### Content Generation Endpoints

| Endpoint | Method | p50 | p95 | p99 | Target | Alert |
|----------|--------|-----|-----|-----|--------|-------|
| `/api/generator/generate-all` | POST | 65s | 85s | 95s | <90s | >120s |
| `/api/generator/regenerate` | POST | 8s | 15s | 20s | <20s | >30s |
| `/api/generator/export` | POST | 2s | 5s | 8s | <10s | >15s |

**Notes:**
- `generate-all` time varies with post count (30 posts baseline)
- Async generation enabled (`PARALLEL_GENERATION=True`)
- Max concurrent API calls: 5

### CRUD Endpoints

| Endpoint | Method | p50 | p95 | p99 | Target | Alert |
|----------|--------|-----|-----|-----|--------|-------|
| `/api/clients` (list) | GET | 45ms | 120ms | 180ms | <200ms | >500ms |
| `/api/clients/{id}` | GET | 25ms | 60ms | 90ms | <100ms | >300ms |
| `/api/clients` | POST | 80ms | 150ms | 200ms | <250ms | >500ms |
| `/api/projects` (list) | GET | 60ms | 140ms | 200ms | <250ms | >600ms |
| `/api/projects/{id}` | GET | 30ms | 75ms | 110ms | <150ms | >400ms |
| `/api/posts` (list) | GET | 55ms | 130ms | 190ms | <200ms | >500ms |
| `/api/posts` (filter) | GET | 70ms | 160ms | 230ms | <300ms | >700ms |

**Notes:**
- Measurements with connection pooling enabled
- Cursor pagination active (20 items per page)
- Includes database query + serialization time

### Research Endpoints

| Endpoint | Method | p50 | p95 | p99 | Target | Alert |
|----------|--------|-----|-----|-----|--------|-------|
| `/api/research/audience` | POST | 15s | 25s | 35s | <30s | >45s |
| `/api/research/competitive` | POST | 18s | 28s | 38s | <35s | >50s |
| `/api/research/content-gap` | POST | 20s | 30s | 40s | <40s | >60s |
| `/api/research/seo-keywords` | POST | 12s | 22s | 30s | <25s | >40s |

---

## Database Performance

### Query Performance

| Query Type | p50 | p95 | p99 | Target | Alert |
|------------|-----|-----|-----|--------|-------|
| Simple SELECT (by ID) | 5ms | 15ms | 25ms | <50ms | >100ms |
| JOIN (2 tables) | 12ms | 30ms | 45ms | <100ms | >200ms |
| JOIN (3+ tables) | 25ms | 60ms | 90ms | <150ms | >300ms |
| Aggregate (COUNT, AVG) | 18ms | 45ms | 70ms | <120ms | >250ms |
| Full-text search | 30ms | 80ms | 120ms | <200ms | >400ms |

### Connection Pool

| Metric | Baseline | Target | Alert |
|--------|----------|--------|-------|
| **Pool Size** | 20 | - | - |
| **Max Overflow** | 40 | - | - |
| **Active Connections** | 8 (avg) | <50 | >55 |
| **Idle Connections** | 5 (avg) | <10 | >15 |
| **Wait Time** | <10ms | <50ms | >100ms |
| **Connection Errors** | 0 | 0 | >1/hr |

---

## Frontend Performance

### Page Load Times

| Page | First Paint | Interactive | Full Load | Target | Alert |
|------|-------------|-------------|-----------|--------|-------|
| **Login** | 350ms | 800ms | 1.2s | <2s | >3s |
| **Dashboard** | 450ms | 1.1s | 1.8s | <3s | >5s |
| **Wizard (Step 1)** | 400ms | 900ms | 1.5s | <2.5s | >4s |
| **Content Review** | 500ms | 1.3s | 2.2s | <4s | >6s |
| **Project Detail** | 420ms | 950ms | 1.6s | <3s | >5s |

**Measurement Conditions:**
- Chrome DevTools Performance tab
- Fast 3G throttling
- Desktop viewport (1920x1080)
- React production build

### JavaScript Bundle Size

| Bundle | Size (gzip) | Baseline | Target | Alert |
|--------|-------------|----------|--------|-------|
| **Vendor** | 280 KB | 280 KB | <400 KB | >500 KB |
| **Main** | 120 KB | 120 KB | <200 KB | >300 KB |
| **Chunk (avg)** | 45 KB | 45 KB | <100 KB | >150 KB |
| **Total** | 445 KB | 445 KB | <700 KB | >1 MB |

---

## Resource Utilization

### CPU Usage

| Scenario | Baseline | Target | Alert |
|----------|----------|--------|-------|
| **Idle** | 5% | <10% | >20% |
| **Light load** (1 user) | 15% | <30% | >50% |
| **Medium load** (5 users) | 40% | <60% | >75% |
| **Heavy load** (10 users) | 70% | <85% | >90% |
| **Generation peak** | 85% | <95% | >98% |

**Notes:**
- 4 CPU cores (2.4 GHz)
- Spikes during parallel generation normal
- Alert if sustained >75% for 5+ minutes

### Memory Usage

| Scenario | Baseline | Target | Alert |
|----------|----------|--------|-------|
| **Startup** | 450 MB | <600 MB | >800 MB |
| **Idle** | 550 MB | <800 MB | >1 GB |
| **Active (1 project)** | 750 MB | <1.2 GB | >1.5 GB |
| **Active (5 projects)** | 1.1 GB | <2 GB | >2.5 GB |
| **Peak generation** | 1.8 GB | <3 GB | >3.5 GB |

**Notes:**
- 16 GB RAM available
- Python + FastAPI + React build
- Includes connection pool overhead

### Disk I/O

| Operation | Baseline | Target | Alert |
|-----------|----------|--------|-------|
| **Read IOPS** | 120 | <500 | >1000 |
| **Write IOPS** | 80 | <400 | >800 |
| **Latency (read)** | 8ms | <20ms | >50ms |
| **Latency (write)** | 12ms | <30ms | >80ms |

---

## Throughput Benchmarks

### Concurrent Users

| Users | Req/sec | Success Rate | p95 Latency | Notes |
|-------|---------|--------------|-------------|-------|
| **1** | 25 | 100% | 180ms | Single operator |
| **5** | 110 | 99.8% | 320ms | Small team |
| **10** | 200 | 99.2% | 550ms | Full team |
| **20** | 350 | 97.5% | 850ms | Peak hours |
| **50** | 650 | 93.0% | 1.8s | Stress test |

**Alert Thresholds:**
- Success rate < 98% for 5+ minutes
- p95 latency > 1s for sustained period

### Content Generation Throughput

| Scenario | Posts/hr | Projects/hr | Success Rate |
|----------|----------|-------------|--------------|
| **Single operator** | 360 | 12 | 99.5% |
| **3 operators** | 950 | 32 | 99.2% |
| **5 operators** | 1,450 | 48 | 98.8% |
| **10 operators** | 2,600 | 87 | 97.5% |

**Notes:**
- Assumes 30 posts per project
- Includes generation + QA + export time
- Anthropic API rate limits enforced (70% threshold)

---

## Regression Testing

### How to Measure

```bash
# 1. Backend API performance
ab -n 1000 -c 10 http://localhost:8000/api/clients
# Requests per second: ~450 (target)

# 2. Frontend load time (Lighthouse CLI)
lighthouse https://your-app.com --output=json --output-path=lighthouse-report.json
# Performance score: >85 (target)

# 3. Database query performance
EXPLAIN ANALYZE SELECT * FROM posts WHERE project_id = 'xxx';
# Execution time: <50ms (target)

# 4. Generation end-to-end
time python run_jumpstart.py tests/fixtures/sample_brief.txt
# Total time: <90s for 30 posts (target)
```

### Automated Regression Tests

Run weekly and on every major release:

```bash
# Run performance test suite
pytest tests/performance/ --benchmark-only

# Generate performance report
python scripts/generate_performance_report.py > performance-report.md
```

---

## Historical Data

### Baseline Evolution

| Version | Date | API p95 | DB p95 | Gen Time | Notes |
|---------|------|---------|--------|----------|-------|
| v1.0.0 | 2025-01-01 | 180ms | 50ms | 240s | Sync generation |
| v1.1.0 | 2025-02-01 | 165ms | 45ms | 90s | Async enabled |
| v1.2.0 | 2025-03-01 | 155ms | 40ms | 75s | Connection pooling |
| v1.3.0 | TBD | TBD | TBD | TBD | Current |

**Improvement Goals:**
- API p95: Reduce by 10% each quarter
- Database p95: Maintain <50ms
- Generation time: Target 60s for 30 posts

---

## Capacity Planning

### Current Capacity

- **Max concurrent projects:** 10
- **Max concurrent operators:** 20
- **Posts per day:** ~20,000
- **Database size:** ~10 GB

### Growth Projections

| Metric | 3 Months | 6 Months | 12 Months | Notes |
|--------|----------|----------|-----------|-------|
| **Users** | 30 | 50 | 100 | 2x every 6 months |
| **Projects/day** | 150 | 300 | 600 | Linear with users |
| **Database size** | 30 GB | 60 GB | 150 GB | ~500 MB/project |
| **API calls/min** | 5,000 | 10,000 | 20,000 | Rate limit headroom |

### Scaling Triggers

**Horizontal Scaling (Add instances):**
- CPU usage >75% for 30+ minutes
- Request queue length >100
- p95 latency >500ms sustained

**Vertical Scaling (Upgrade resources):**
- Memory usage >85%
- Database IOPS >80% capacity
- Connection pool exhaustion

**Database Scaling:**
- Storage >80% full
- Query latency >200ms p95
- Connection pool saturated

---

**Document Control:**
- **Version:** 1.0
- **Last Benchmark:** 2025-12-29
- **Next Benchmark:** 2026-01-29 (monthly)
- **Owner:** Performance Team
