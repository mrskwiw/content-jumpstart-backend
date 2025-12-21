# Bug Fix: "Failed to load projects" Error

## Issues Found

### 1. Missing Database Column (PRIMARY ISSUE)
**Error:** `sqlite3.OperationalError: no such column: deliverables_1.file_size_bytes`

**Root Cause:** The `deliverables` table was missing the `file_size_bytes` column that was added to the Deliverable model during the file download feature implementation.

**Impact:** When loading projects, the API tries to eager-load related deliverables, which failed due to the missing column.

**Fix Applied:** Added migration script `add_file_size_bytes.py` which adds the column to the database.

### 2. Incorrect Serialization Format (SECONDARY ISSUE)
**Error:** Frontend expects camelCase (`clientId`, `createdAt`) but backend was sending snake_case (`client_id`, `created_at`)

**Root Cause:** The `ProjectResponse` schema has an `alias_generator` that converts snake_case to camelCase, but the backend was calling `model_dump()` without the `by_alias=True` parameter.

**Fix Applied:** Updated all `model_dump()` calls in `backend/routers/projects.py` to use `by_alias=True`.

## Files Modified

1. **add_file_size_bytes.py** (NEW)
   - Migration script to add missing column
   - Safe to run multiple times (checks if column exists first)

2. **backend/routers/projects.py** (UPDATED)
   - Line 72: Added `by_alias=True` to list endpoint
   - Line 111: Added `by_alias=True` to create endpoint
   - Line 144: Added `by_alias=True` to get endpoint
   - Line 175: Added `by_alias=True` to update endpoint

## How to Apply Fixes

### Automatic Migration (Docker & Local)
**NEW:** The migration now runs automatically when the backend starts up!

The `backend/database.py` file has been updated to include auto-migration logic in the `init_db()` function. This ensures the database schema is updated both locally and in Docker containers without manual intervention.

On startup, you should see:
```
>> Running migration: Adding file_size_bytes column to deliverables table
>> Migration completed successfully
```

### For Docker Deployments
```bash
# Rebuild the Docker image to include the updated code
docker-compose build

# Start the containers
docker-compose up -d

# Check logs to verify migration ran
docker-compose logs api | grep -i migration
```

### For Local Development
```bash
# Stop the current backend (Ctrl+C in the terminal running uvicorn)
# Then restart:
cd backend
uvicorn main:app --reload --port 8000

# Migration will run automatically on startup
```

### Manual Migration (Legacy - No Longer Needed)
The `add_file_size_bytes.py` script is still available for manual migration if needed, but the automatic migration in `init_db()` makes this unnecessary.

### Test in Dashboard
1. Navigate to the Projects page in the operator dashboard
2. Projects should now load correctly
3. Verify that demo clients and projects are visible

## Verification

Run the test script to verify the fix:
```bash
python test_projects_api.py
```

Expected output:
```
Found X projects in database
[SUCCESS] Pydantic serialization successful!
Keys (camelCase): ['name', 'clientId', 'templates', 'platforms', 'tone', 'id', 'status', 'createdAt', 'updatedAt']
```

## Why This Happened

The `file_size_bytes` column was added to the Deliverable model (likely in Phase 15 when implementing the download feature), but:
1. No database migration was created
2. The backend was restarted without running migrations
3. The schema mismatch only became apparent when eager-loading projects with deliverables
4. **Docker containers had separate databases** that didn't get migrated when running the local migration script

## Docker-Specific Issue

When the user reported "still getting Failed to load projects. after a rebuild of the image", this revealed that:
- Local database was fixed by running `add_file_size_bytes.py`
- Docker container has its own database volume that wasn't migrated
- Manual migration scripts don't run inside Docker containers on build

**Solution:** Auto-migration logic in `backend/database.py` ensures all environments (local and Docker) get the schema updates automatically on startup.

## Prevention

To prevent similar issues:
1. Always create migration scripts when adding database columns
2. **Add auto-migration logic to init_db() for critical schema changes** (ensures Docker compatibility)
3. Document schema changes in phase completion docs
4. Use proper database migration tools (Alembic) for production
5. Test API endpoints after schema changes in **both local and Docker environments**

## Related Files

- `backend/models/deliverable.py` - Deliverable model definition
- `backend/schemas/project.py` - ProjectResponse schema with alias_generator
- `test_projects_api.py` - Test script for verifying the fix
