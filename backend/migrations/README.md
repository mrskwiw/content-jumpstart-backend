# Database Migrations

This directory contains SQL migration scripts for the Content Jumpstart backend database.

## Overview

Since the backend doesn't use Alembic yet, database schema changes are managed through:
1. **SQLAlchemy models** - New tables/columns automatically created on startup
2. **SQL migration scripts** - Manual execution for existing databases

## Migration Scripts

### 001_add_cursor_pagination_indexes.sql

**Purpose:** Add composite indexes for cursor-based pagination (Week 3 optimization)

**Applies to:**
- `projects` table
- `posts` table

**Performance Impact:**
- Deep pagination: 6x-67x faster
- O(n) → O(1) performance for large datasets

**How to apply:**

```bash
# PostgreSQL
psql -U username -d database_name -f 001_add_cursor_pagination_indexes.sql

# SQLite (development)
sqlite3 backend.db < 001_add_cursor_pagination_indexes.sql
```

**Verification:**

```sql
-- Check if indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE indexname LIKE 'ix_%_created_at_id';
```

## Creating New Migrations

When adding new schema changes:

1. **Update SQLAlchemy models** in `backend/models/`
2. **Create SQL migration script** in this directory
   - Naming: `{number}_{description}.sql`
   - Include rollback instructions
   - Document purpose and impact
3. **Test locally** before production
4. **Document in README**

## Best Practices

- Use `IF NOT EXISTS` to make migrations idempotent
- Include comments explaining the change
- Test migrations on a copy of production data
- Keep migrations small and focused
- Never delete old migration files

## Future: Alembic Integration

Once the backend matures, consider migrating to Alembic for:
- Automatic migration generation
- Version tracking
- Rollback capabilities
- Migration history

**Setup Alembic:**
```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```
