# Demo Data Seeding Guide

## Overview

This guide explains how to populate the backend database with demo/development data for testing the operator dashboard.

**⚠️ WARNING:** This demo data is for **DEVELOPMENT/TESTING ONLY**. It must be purged before deploying to production.

---

## Quick Start

### Seed Database with Demo Data

```bash
cd backend
python seed_demo_data.py
```

This will populate the database with:
- **15 clients** across diverse industries (B2B SaaS, Healthcare, Fintech, EdTech, etc.)
- **27 projects** with various statuses (delivered, ready, qa, generating, draft)
- **10 runs** (7 succeeded, 2 running, 1 failed)
- **10 posts** with realistic content and quality metrics
- **15 deliverables** (7 delivered, 7 ready, 1 draft)

### Clear Demo Data Only

```bash
cd backend
python seed_demo_data.py --clear-only
```

This removes all demo data without re-seeding.

---

## Demo Data Details

### Clients (15)

Sample clients across industries:
- **Acme Corp** - B2B SaaS Enterprise
- **TechVision AI** - AI Technology
- **GrowthLab Marketing** - Marketing Agency
- **FinanceFlow Solutions** - Fintech
- **HealthTech Innovations** - Healthcare Technology
- **EduPro Learning** - EdTech
- **SecureNet Cybersecurity** - Cybersecurity
- **WanderLust Travel** - Travel & Tourism
- **CloudScale Infrastructure** - Cloud Services
- **RetailBoost POS** - Retail Technology
- **ContentCraft Agency** - Content Marketing
- **FitWell Wellness** - Health & Wellness
- **DataSense Analytics** - Data Analytics
- **UrbanSpace Real Estate** - Real Estate
- **NextGen Startups** - Startup Incubator

### Projects (27)

Projects distributed across clients with:
- **Status variety**: delivered (7), ready (6), qa (3), generating (2), draft (9)
- **Platform mix**: LinkedIn, Twitter, Blog, Facebook, Instagram
- **Tone diversity**: professional, conversational, technical, motivational, analytical, empathetic, innovative, inspirational
- **Template usage**: All 15 template types represented

### Runs (10)

- **7 succeeded runs** - Completed successfully with logs
- **2 running runs** - Currently in progress
- **1 failed run** - With error message (if implemented)

### Posts (10)

Sample posts with:
- Word counts: 198-312 words
- Readability scores: 66.9-75.8
- Various templates: Problem Recognition, Statistic + Insight, Personal Story, Inside Look, How-To, Myth Busting
- Quality flags: Some posts flagged with "missing_cta"
- Platform variety: Primarily LinkedIn

### Deliverables (15)

- **7 delivered** - With delivery timestamps, proof URLs, and notes
- **7 ready** - Prepared for delivery
- **1 draft** - Still in progress

---

## Environment Safety

### Environment Check

The seed script automatically checks the `ENVIRONMENT` variable and **refuses to run in production**:

```bash
# This will fail if ENVIRONMENT=production
python seed_demo_data.py
```

**Error message:**
```
❌ ERROR: Cannot run seed script in PRODUCTION environment!
   Set ENVIRONMENT=development to proceed.
```

### Recommended Environment Variables

**Development (.env):**
```env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/operator.db
```

**Production (.env.production):**
```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/content_jumpstart
```

---

## Production Deployment Warning

**⚠️ CRITICAL: Before deploying to production, you MUST purge all demo data!**

### Option 1: Drop and Recreate Database (Recommended)

**PostgreSQL:**
```bash
dropdb content_jumpstart
createdb content_jumpstart
python -c "from database import init_db; init_db()"
```

**SQLite:**
```bash
rm data/operator.db
python -c "from database import init_db; init_db()"
```

### Option 2: Clear Data Only

```bash
python seed_demo_data.py --clear-only
```

### Verification

**PostgreSQL:**
```bash
psql -d content_jumpstart -c "SELECT COUNT(*) FROM clients;"
# Expected output: 0
```

**SQLite:**
```bash
sqlite3 data/operator.db "SELECT COUNT(*) FROM clients;"
# Expected output: 0
```

---

## Frontend Integration

### Using Real Backend (Default)

**operator-dashboard/.env:**
```env
VITE_USE_MOCKS=false
VITE_API_URL=http://localhost:8000
```

This configuration connects the dashboard to the real backend API, showing the seeded data.

### Using Mock Data

**operator-dashboard/.env:**
```env
VITE_USE_MOCKS=true
VITE_API_URL=http://localhost:8000
```

This configuration uses the mock data from `operator-dashboard/src/mocks/data.ts`.

---

## Troubleshooting

### Issue: "Cannot import models" Error

**Cause:** Running from wrong directory

**Solution:**
```bash
cd backend  # Must be in backend directory
python seed_demo_data.py
```

### Issue: Unicode Encoding Error (Windows)

**Cause:** Windows console doesn't support UTF-8 by default

**Solution:** The script automatically fixes this via UTF-8 wrapper. If issues persist:
```bash
chcp 65001  # Set console to UTF-8
python seed_demo_data.py
```

### Issue: Database Lock Error (SQLite)

**Cause:** Backend server or dashboard still connected to database

**Solution:**
```bash
# Stop backend server
# Stop dashboard dev server
python seed_demo_data.py
```

### Issue: Foreign Key Constraint Errors

**Cause:** Data relationships are invalid

**Solution:** Use `--clear-only` first, then re-seed:
```bash
python seed_demo_data.py --clear-only
python seed_demo_data.py
```

---

## Advanced Usage

### Custom Timestamp Ranges

Edit `seed_demo_data.py` and modify `base_time`:

```python
# Default: Current time
base_time = datetime.now()

# Custom: Specific date
base_time = datetime(2025, 12, 1, 12, 0, 0)
```

### Adding More Demo Data

Edit the seed functions in `seed_demo_data.py`:

```python
def seed_clients(db):
    clients = [
        # ... existing clients ...
        Client(id="client-16", name="NewCorp", email="info@newcorp.com"),
    ]
```

### Partial Seeding

Comment out unwanted seed calls in `main()`:

```python
# Seed specific data only
seed_clients(db)
seed_projects(db)
# seed_runs(db)      # Skip runs
# seed_posts(db)     # Skip posts
# seed_deliverables(db)  # Skip deliverables
```

---

## Related Documentation

- **Production Deployment:** `PRODUCTION_DEPLOYMENT.md` - Complete deployment guide with data purge instructions
- **Backend README:** `README.md` - Backend setup and configuration
- **Frontend Integration:** `../operator-dashboard/README.md` - Dashboard setup
- **Mock Data:** `../operator-dashboard/src/mocks/data.ts` - TypeScript mock data structure

---

## Summary

**Development Workflow:**
1. Start backend: `uvicorn main:app --reload`
2. Seed database: `python seed_demo_data.py`
3. Start dashboard: `cd ../operator-dashboard && npm run dev`
4. Dashboard shows seeded data at http://localhost:5173

**Production Checklist:**
- [ ] Purge all demo data (`--clear-only` or drop database)
- [ ] Verify database is empty (0 clients)
- [ ] Set `ENVIRONMENT=production`
- [ ] Use production database URL
- [ ] Deploy application

**Support:**
- Questions: See backend README.md
- Issues: Check troubleshooting section above
- Deployment: See PRODUCTION_DEPLOYMENT.md

---

**Last Updated:** December 17, 2025
**Version:** 1.0.0
