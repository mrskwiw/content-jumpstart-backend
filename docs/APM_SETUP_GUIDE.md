# Application Performance Monitoring (APM) Setup Guide

**Version:** 1.0
**Last Updated:** 2025-12-29
**Recommended Tools:** Datadog, New Relic, Sentry

This guide provides instructions for setting up comprehensive application performance monitoring.

---

## Table of Contents

1. [Overview](#overview)
2. [Recommended APM Solutions](#recommended-apm-solutions)
3. [Datadog Setup (Recommended)](#datadog-setup-recommended)
4. [Sentry Setup (Error Tracking)](#sentry-setup-error-tracking)
5. [Custom Metrics](#custom-metrics)
6. [Alerting](#alerting)
7. [Cost Optimization](#cost-optimization)

---

## Overview

### What We Monitor

**Application Metrics:**
- API response times (p50, p95, p99)
- Error rates by endpoint
- Request throughput
- Database query performance
- Cache hit/miss rates
- Generation success rates

**Infrastructure Metrics:**
- CPU, memory, disk usage
- Network I/O
- Database connections
- Queue depths

**Business Metrics:**
- Posts generated per hour
- Active projects
- Revenue per customer
- Conversion rates

---

## Recommended APM Solutions

### Option 1: Datadog (Recommended) ⭐

**Pros:**
- Complete APM + infrastructure monitoring
- Excellent Python/FastAPI support
- Built-in distributed tracing
- Custom dashboards and alerting

**Cons:**
- Higher cost ($15-31/host/month)

**Best For:** Production deployments, teams >5 people

### Option 2: New Relic

**Pros:**
- Strong APM features
- Good free tier
- Easy setup

**Cons:**
- More expensive at scale
- Less flexible dashboards

**Best For:** Startups, free tier acceptable

### Option 3: Sentry + Prometheus

**Pros:**
- Best error tracking (Sentry)
- Open-source metrics (Prometheus)
- Lower cost

**Cons:**
- More setup required
- Separate tools to manage

**Best For:** Cost-conscious teams, self-hosted preferred

---

## Datadog Setup (Recommended)

### 1. Installation

```bash
# Add Datadog to requirements.txt
echo "ddtrace==2.3.0" >> requirements.txt
pip install -r requirements.txt
```

### 2. FastAPI Integration

**`backend/main.py`:**

```python
from ddtrace import patch_all, tracer
from ddtrace.contrib.fastapi import TraceMiddleware

# Patch all supported libraries
patch_all()

# Add tracer middleware
app.add_middleware(
    TraceMiddleware,
    tracer=tracer,
    service_name="content-jumpstart-api",
    distributed_tracing=True,
)

# Configure tracer
tracer.configure(
    hostname="datadog-agent",  # Or Datadog cloud
    port=8126,
    https=False,
    priority_sampling=True,
    analytics_enabled=True,
    tags={
        "env": os.getenv("ENVIRONMENT", "production"),
        "version": settings.API_VERSION,
    }
)
```

### 3. Database Tracing

```python
from ddtrace import patch

# Patch SQLAlchemy
patch(sqlalchemy=True)

# In database.py, add span tags
from ddtrace import tracer

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
)

# Add custom span for queries
@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    with tracer.trace("db.query", service="postgres") as span:
        span.set_tag("sql.query", statement[:100])  # First 100 chars
```

### 4. Custom Metrics

**`backend/utils/metrics.py`:**

```python
from datadog import initialize, statsd

# Initialize Datadog
initialize(
    statsd_host="localhost",
    statsd_port=8125,
)

class Metrics:
    @staticmethod
    def increment(metric_name, value=1, tags=None):
        """Increment a counter"""
        statsd.increment(metric_name, value=value, tags=tags or [])

    @staticmethod
    def gauge(metric_name, value, tags=None):
        """Set a gauge value"""
        statsd.gauge(metric_name, value, tags=tags or [])

    @staticmethod
    def histogram(metric_name, value, tags=None):
        """Record a histogram value"""
        statsd.histogram(metric_name, value, tags=tags or [])

    @staticmethod
    def timing(metric_name, duration_ms, tags=None):
        """Record timing"""
        statsd.timing(metric_name, duration_ms, tags=tags or [])

# Usage in code
metrics = Metrics()

# Track generation success
metrics.increment("content.generation.success", tags=["client:acme"])

# Track generation time
metrics.timing("content.generation.duration", 65000, tags=["posts:30"])

# Track active projects
metrics.gauge("projects.active", 15)
```

### 5. Environment Variables

```bash
# .env
DD_AGENT_HOST=datadog-agent  # Or dd-agent for cloud
DD_TRACE_ENABLED=true
DD_SERVICE=content-jumpstart
DD_ENV=production
DD_VERSION=1.0.0
DD_LOGS_INJECTION=true  # Add trace IDs to logs
DD_PROFILING_ENABLED=true  # Enable profiling
```

### 6. Docker Compose Integration

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - DD_AGENT_HOST=datadog-agent
      - DD_TRACE_ENABLED=true

  datadog-agent:
    image: gcr.io/datadoghq/agent:latest
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=datadoghq.com
      - DD_LOGS_ENABLED=true
      - DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true
      - DD_APM_ENABLED=true
      - DD_APM_NON_LOCAL_TRAFFIC=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
```

---

## Sentry Setup (Error Tracking)

### 1. Installation

```bash
pip install sentry-sdk[fastapi]==1.40.0
```

### 2. Integration

**`backend/main.py`:**

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "production"),
    release=f"content-jumpstart@{settings.API_VERSION}",
    traces_sample_rate=0.1,  # Sample 10% of transactions
    profiles_sample_rate=0.1,  # Sample 10% for profiling
    integrations=[
        FastApiIntegration(transaction_style="url"),
        SqlalchemyIntegration(),
    ],
    before_send=filter_sensitive_data,  # Filter PII
)

def filter_sensitive_data(event, hint):
    """Remove sensitive data before sending to Sentry"""
    # Remove API keys from request data
    if "request" in event:
        if "data" in event["request"]:
            event["request"]["data"] = "[FILTERED]"
        if "headers" in event["request"]:
            if "Authorization" in event["request"]["headers"]:
                event["request"]["headers"]["Authorization"] = "[FILTERED]"
    return event
```

### 3. Custom Error Context

```python
from sentry_sdk import capture_exception, set_context, set_tag

try:
    posts = generate_posts(client_brief)
except Exception as e:
    # Add context before capturing
    set_context("generation", {
        "client": client_brief.company_name,
        "num_posts": num_posts,
        "platform": platform.value,
    })
    set_tag("error_type", "generation_failure")
    capture_exception(e)
    raise
```

---

## Custom Metrics

### Business Metrics to Track

**`backend/utils/business_metrics.py`:**

```python
from utils.metrics import Metrics

metrics = Metrics()

def track_generation_success(client_name, num_posts, duration_s):
    """Track successful content generation"""
    tags = [
        f"client:{client_name}",
        f"posts:{num_posts}",
    ]
    metrics.increment("business.generation.success", tags=tags)
    metrics.timing("business.generation.duration", duration_s * 1000, tags=tags)

def track_generation_failure(client_name, error_type):
    """Track failed generation"""
    tags = [
        f"client:{client_name}",
        f"error_type:{error_type}",
    ]
    metrics.increment("business.generation.failure", tags=tags)

def track_revenue(client_name, amount_usd, tier):
    """Track revenue"""
    tags = [
        f"client:{client_name}",
        f"tier:{tier}",
    ]
    metrics.gauge("business.revenue.total", amount_usd, tags=tags)
    metrics.increment("business.projects.completed", tags=tags)

def track_active_users(count):
    """Track active operators"""
    metrics.gauge("business.users.active", count)
```

### Performance Metrics

**`backend/middleware/performance.py`:**

```python
import time
from fastapi import Request
from utils.metrics import Metrics

metrics = Metrics()

@app.middleware("http")
async def track_performance(request: Request, call_next):
    """Track request performance"""
    start_time = time.time()

    # Track request
    metrics.increment("api.requests", tags=[
        f"method:{request.method}",
        f"path:{request.url.path}",
    ])

    try:
        response = await call_next(request)

        # Track success
        duration_ms = (time.time() - start_time) * 1000
        metrics.timing("api.response_time", duration_ms, tags=[
            f"method:{request.method}",
            f"path:{request.url.path}",
            f"status:{response.status_code}",
        ])

        if response.status_code >= 400:
            metrics.increment("api.errors", tags=[
                f"status:{response.status_code}",
                f"path:{request.url.path}",
            ])

        return response

    except Exception as e:
        # Track exception
        metrics.increment("api.exceptions", tags=[
            f"type:{type(e).__name__}",
            f"path:{request.url.path}",
        ])
        raise
```

---

## Alerting

### Critical Alerts

**Datadog Monitors:**

```yaml
# config/datadog/monitors.yaml
monitors:
  - name: "High API Error Rate"
    type: metric alert
    query: "sum(last_5m):sum:api.errors{*} by {path}.as_rate() > 10"
    message: |
      API error rate >10% for {{path.name}}
      @slack-#alerts @pagerduty
    priority: critical

  - name: "Slow API Response"
    type: metric alert
    query: "avg(last_10m):avg:api.response_time{*} by {path} > 500"
    message: |
      API response time >500ms for {{path.name}}
      p95: {{value}} ms
      @slack-#alerts
    priority: high

  - name: "Generation Failures"
    type: metric alert
    query: "sum(last_15m):sum:business.generation.failure{*} > 3"
    message: |
      Multiple generation failures detected
      Check logs and Anthropic API status
      @slack-#alerts
    priority: high

  - name: "Database Slow Queries"
    type: metric alert
    query: "avg(last_10m):avg:db.query.duration{*} > 200"
    message: |
      Database queries running slow (>200ms avg)
      Review slow query log
      @slack-#performance
    priority: medium
```

### Warning Alerts

```yaml
monitors:
  - name: "Memory Usage High"
    type: metric alert
    query: "avg(last_5m):avg:system.mem.used{*} / avg:system.mem.total{*} > 0.85"
    message: |
      Memory usage >85%
      Consider scaling up
      @slack-#ops
    priority: medium

  - name: "CPU Usage High"
    type: metric alert
    query: "avg(last_5m):avg:system.cpu.idle{*} < 15"
    message: |
      CPU usage >85% sustained
      @slack-#ops
    priority: medium
```

---

## Cost Optimization

### Sampling Strategy

```python
# Only sample 10% of traces in production
traces_sample_rate = 0.1 if PRODUCTION else 1.0

# Sample errors at 100%
error_sample_rate = 1.0

# Profile 5% of requests
profiles_sample_rate = 0.05
```

### Tag Cardinality

Avoid high-cardinality tags (e.g., user IDs, timestamps):

```python
# ❌ Bad - high cardinality
tags = [f"user:{user_id}"]  # Millions of unique tags

# ✅ Good - low cardinality
tags = [f"user_tier:{user.tier}"]  # Only 4 unique tags
```

### Retention Policies

- **Metrics:** 15 months retention
- **Traces:** 15 days retention (sampled)
- **Logs:** 7 days retention (indexed), 30 days archive
- **Profiles:** 7 days retention

---

**Document Control:**
- **Version:** 1.0
- **Last Review:** 2025-12-29
- **Next Review:** 2026-01-29 (monthly)
- **Owner:** DevOps Team
