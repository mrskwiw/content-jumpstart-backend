# Known Bugs

This file tracks known bugs and issues in the application.

## Active Bugs

### 11. Cost Tracker SQL Error - Misuse of aggregate MAX()

**Status:** ✅ RESOLVED (January 5, 2026)
**Severity:** Low - Affects cost tracking only, not content generation
**Component:** Cost Tracker Utility
**Location:** `src/utils/cost_tracker.py:387`

**Description:**
The `get_all_projects()` method failed with SQL error "misuse of aggregate: MAX()" when trying to retrieve all project IDs sorted by most recent activity.

**Steps to Reproduce:**
1. Run pytest on tests/unit/test_cost_tracker.py::test_get_all_projects
2. SQL error occurs

**Expected vs. Actual Behavior:**
- Expected: Get list of project IDs sorted by most recent API call
- Actual: SQLite error "misuse of aggregate: MAX()"

**Root Cause:**
SQL query used `ORDER BY MAX(timestamp)` without a `GROUP BY` clause, which is invalid in SQLite.

**Solution:**
Fixed SQL query to use `GROUP BY project_id` and select the MAX(timestamp) as an aliased column:
```sql
SELECT project_id, MAX(timestamp) as last_call
FROM api_calls
GROUP BY project_id
ORDER BY last_call DESC
```

**Files Changed:**
- `project/src/utils/cost_tracker.py` - Fixed lines 387-393

**Date Reported:** January 5, 2026
**Resolution Date:** January 5, 2026
**Source:** Unit test failure during bug verification

---

### 8. SQLAlchemy Session Error - Project instance not bound to Session

**Status:** ✅ RESOLVED (December 31, 2025)
**Severity:** Critical - Blocks generation completely
**Component:** Backend / Database Session Management
**Location:** Wizard Generate step (Step 4)

**Description:**
When attempting to generate content via the wizard, the backend fails with error: "Instance <Project at 0x79638cc1B3d0> is not bound to a Session; attribute refresh operation cannot proceed (Background on this error at: https://sqlalche.me/e/20/bhk3)"

**Steps to Reproduce:**
1. Navigate to Wizard/QA page
2. Complete all wizard steps (Client Profile, Research, Templates)
3. Click "Generate All" button on Generate step (Step 4)
4. Error appears blocking generation

**Expected vs. Actual Behavior:**
- Expected: Content generation starts successfully
- Actual: SQLAlchemy session error blocks generation

**Affected Component:** Backend database session management in generation endpoints

**Potential Causes:**
- Project object loaded in one session but used in another
- Session not being passed correctly to background tasks
- Database session closed prematurely before async generation completes

**Solution:**
Fixed database session management in `backend/routers/generator.py`. The issue was that `crud.update_run()` returns a refreshed instance, but the code was trying to refresh the old instance. Changed line 171 to capture the return value: `db_run = crud.update_run(db, db_run.id, status="running")` and removed the redundant `db.refresh(db_run)` call.

**Files Changed:**
- `project/backend/routers/generator.py` - Fixed session management on lines 171-175

**Date Reported:** December 31, 2025
**Resolution Date:** December 31, 2025
**Source:** Error image review (error images/image.png)

---

### 9. Import Error - Relative import beyond top-level package

**Status:** ✅ RESOLVED (December 31, 2025)
**Severity:** Critical - Blocks generation completely
**Component:** Backend / Python Module Imports
**Location:** Wizard Generate step (Step 4)

**Description:**
Content generation fails with error: "Generation failed: attempted relative import beyond top-level package"

**Steps to Reproduce:**
1. Navigate to Wizard/QA page
2. Complete all wizard steps
3. Click "Generate All" button
4. Error appears blocking generation

**Expected vs. Actual Behavior:**
- Expected: Content generation starts successfully
- Actual: Import error blocks generation

**Affected Component:** Python module import structure in backend

**Potential Causes:**
- Incorrect relative import statement (e.g., `from ...module import X`)
- Module attempting to import from parent package incorrectly
- Circular import dependency
- Python path configuration issue

**Solution:**
Fixed Python module import path in `backend/services/generator_service.py`. The issue was that the code was adding `src/` to `sys.path`, making it the top-level package, causing relative imports in `src/agents/content_generator.py` to fail when trying to go beyond the top level. Changed lines 221-236 to add the project root instead and use `from src.agents...` style imports.

**Files Changed:**
- `project/backend/services/generator_service.py` - Fixed sys.path manipulation and imports on lines 221-236

**Date Reported:** December 31, 2025
**Resolution Date:** December 31, 2025
**Source:** Error image review (error images/image (1).png)

---

### 10. Generic Generation Failure - No error details provided

**Status:** ✅ RESOLVED (December 31, 2025)
**Severity:** High - Blocks generation but error message unhelpful
**Component:** Error Handling / Reporting System
**Location:** Wizard Generate step (Step 4)

**Description:**
Content generation fails with unhelpful error message: "Generation failed: Generation failed:" (no specific error details)

**Steps to Reproduce:**
1. Navigate to Wizard/QA page
2. Complete all wizard steps
3. Click "Generate All" button
4. Generic error message appears with no diagnostic information

**Expected vs. Actual Behavior:**
- Expected: Specific error message indicating what went wrong (file not found, API error, validation failure, etc.)
- Actual: Generic "Generation failed: Generation failed:" with no actionable information

**Affected Component:** Error handling and exception reporting in generation service

**Potential Causes:**
- Exception being caught but not logged properly
- Error message not being propagated from inner exception
- Generic try/catch block swallowing specific error details
- Error handling middleware not configured correctly

**Solution:**
Improved error handling and messages in `backend/services/generator_service.py`. Changed the generic fallback error message from "Generation failed" to "Unknown error - CLI execution failed" and added detailed logging. Also improved error messages in `_generate_with_template_quantities` to include error type and context (lines 130-134 and 363-367).

**Files Changed:**
- `project/backend/services/generator_service.py` - Improved error messages on lines 130-134 and 363-367

**Impact:** Error messages now provide actionable debugging information including error type and context, making it much easier to diagnose generation failures.

**Date Reported:** December 31, 2025
**Resolution Date:** December 31, 2025
**Source:** Error image review (error images/error code 1.pdf)

---

## Resolved Bugs

### 7. Backend fails to start - import error in schemas/post.py

**Status:** ✅ RESOLVED
**Description:** Backend failed to start due to cross-directory import - schemas/post.py imported Platform from src.models.client_brief which doesn't exist in backend context.
**Solution:** Created backend/schemas/enums.py with Platform enum (and other shared enums), updated post.py to import from there, and exported ClientUpdate from schemas/__init__.py.
**Files Changed:** backend/schemas/enums.py (created), backend/schemas/post.py, backend/schemas/__init__.py
**Date Reported:** December 23, 2025
**Resolution Date:** December 23, 2025

---

### 6. Editing existing client creates duplicate instead of updating

**Status:** ✅ RESOLVED
**Description:** Wizard updateClientMutation called non-existent PATCH endpoint and only updated when name changed.
**Solution:** Implemented PATCH endpoint, update_client() CRUD function, and refactored wizard to always update client with all fields.
**Files Changed:** backend/models/client.py, backend/database.py, backend/schemas/client.py, backend/services/crud.py, backend/routers/clients.py, operator-dashboard/src/types/domain.ts, operator-dashboard/src/api/clients.ts, operator-dashboard/src/pages/Wizard.tsx
**Date Reported:** December 23, 2025
**Resolution Date:** December 23, 2025

---

### 5. Selecting existing client doesn't populate form fields

**Status:** ✅ RESOLVED
**Description:** ClientProfilePanel didn't update form when initialData prop changed after client selection.
**Solution:** Added useEffect to sync formData with initialData changes.
**Files Changed:** operator-dashboard/src/components/wizard/ClientProfilePanel.tsx
**Date Reported:** December 23, 2025
**Resolution Date:** December 23, 2025

---

### 4. Save Client button doesn't advance wizard to next page

**Status:** ✅ RESOLVED
**Description:** ClientProfilePanel's handleSubmit was not async and didn't await the onSave callback, causing the wizard to not advance when errors occurred.
**Solution:** Made handleSubmit async with proper await, added loading state, and improved error handling.
**Files Changed:** operator-dashboard/src/components/wizard/ClientProfilePanel.tsx
**Date Reported:** December 23, 2025
**Resolution Date:** December 23, 2025

---

### 3. Dark mode toggle doesn't work

**Status:** ✅ RESOLVED
**Description:** Theme dropdown in Settings page wasn't connected to ThemeContext (no value or onChange props).
**Solution:** Connected dropdown to useTheme hook with value={theme} and onChange handler.
**Files Changed:** operator-dashboard/src/pages/Settings.tsx
**Date Reported:** December 23, 2025
**Resolution Date:** December 23, 2025

---

### 2. System-wide camelCase/snake_case misalignment

**Status:** ✅ RESOLVED (Frontend Workaround)
**Severity:** Medium - Preventive Fix
**Component:** Frontend API Layer
**Location:** Multiple API files in `operator-dashboard/src/api/`

**Description:**
System-wide field naming mismatch between frontend (camelCase) and backend (snake_case) affecting multiple API endpoints.

**Investigation Results:**
Audited all backend schemas and frontend API files:

**Backend Schemas (snake_case):**
- ✅ `project.py` - `client_id` (already fixed)
- ✅ `client.py` - No snake_case fields in Create schema
- ✅ `brief.py` - `project_id`
- ✅ `deliverable.py` - `delivered_at`, `proof_url`, `proof_notes`, `project_id`, `client_id`, `run_id`
- ✅ `post.py` - No Create schema (posts created by generator service)
- ✅ `run.py` - `project_id`, `is_batch`, `completed_at`, `error_message`
- ✅ `auth.py` - `full_name`, `access_token`, `refresh_token` (response only, already handled correctly)

**Solution:**
Added field name conversion in all relevant frontend API files:

1. ✅ **projects.ts** - `clientId` → `client_id` (create)
2. ✅ **generator.ts** - `projectId`, `clientId`, `isBatch`, `postIds` → snake_case
3. ✅ **deliverables.ts** - `projectId`, `clientId`, `runId`, `deliveredAt`, `proofUrl`, `proofNotes` → snake_case
4. ✅ **research.ts** - `projectId`, `clientId` → snake_case
5. ✅ **auth.ts** - Already correct (handles snake_case responses properly)
6. ✅ **posts.ts** - No create/update methods (read-only)
7. ✅ **runs.ts** - No create/update methods (created by generator)
8. ✅ **clients.ts** - No snake_case fields

**Files Changed:**
- `operator-dashboard/src/api/projects.ts` - Added conversion in create()
- `operator-dashboard/src/api/generator.ts` - Added conversion in all 3 methods
- `operator-dashboard/src/api/deliverables.ts` - Added conversion in create() and markDelivered()
- `operator-dashboard/src/api/research.ts` - Added conversion in run()

**Trade-offs:**
- ✅ Prevents 422 validation errors across all endpoints
- ✅ Maintains TypeScript camelCase conventions
- ✅ Centralizes conversion logic in API layer
- ⚠️ Requires manual field mapping (not automatic)
- ⚠️ Developers must remember to add conversion for new endpoints

**Resolution Date:** December 21, 2025
**Date Reported:** December 21, 2025

---

### 1. Wizard fails to create project - 422 validation error

**Status:** ✅ RESOLVED (Frontend Workaround)
**Severity:** High - Was Blocking
**Component:** Backend API / Wizard
**Location:** `operator-dashboard/src/api/projects.ts`

**Original Error:**
```
POST /api/projects returns 422
{"detail": [{"type": "missing", "loc": ["body", "client_id"], "msg": "Field required"}]}
```

**Root Cause:**
- Frontend TypeScript uses camelCase (`clientId`)
- Backend Python/Pydantic uses snake_case (`client_id`)
- FastAPI 0.109.0-0.127.0 does NOT respect Pydantic v2's `validation_alias=AliasChoices`
- Pydantic model validates both formats correctly when tested directly, but FastAPI's request body parsing doesn't honor the validation_alias

**Attempted Backend Fixes (all failed):**
1. ❌ `populate_by_name=True`
2. ❌ `Field(alias='clientId')`
3. ❌ `Field(validation_alias='clientId')`
4. ❌ `Field(validation_alias=AliasChoices('clientId', 'client_id'))`
5. ❌ Upgraded FastAPI 0.109.0 → 0.127.0 and Pydantic 2.5.3 → 2.12.5

**Solution (Frontend Workaround):**
Modified `operator-dashboard/src/api/projects.ts` to convert camelCase to snake_case before sending to backend:

```typescript
async create(input: CreateProjectInput) {
  // Convert camelCase to snake_case for backend compatibility
  const backendInput = {
    name: input.name,
    client_id: input.clientId,  // Convert clientId -> client_id
    templates: input.templates,
    platforms: input.platforms,
    tone: input.tone,
  };
  const { data } = await apiClient.post<Project>('/api/projects', backendInput);
  return data;
}
```

**Files Changed:**
- `operator-dashboard/src/api/projects.ts` - Added field name conversion in create() method

**Tested:**
✅ API endpoint accepts snake_case and creates projects successfully
✅ Wizard can now create clients and projects without 422 errors

**Trade-offs:**
- ✅ Fixes the wizard immediately
- ✅ Maintains TypeScript camelCase conventions in frontend code
- ⚠️ Requires manual field mapping in API layer (not automatic)
- ⚠️ Same pattern needed for other create/update endpoints system-wide

**Resolution Date:** December 21, 2025
**Date Reported:** December 21, 2025

---

## How to Report a Bug

When reporting a bug, include:
1. **Description** - What happens vs. what should happen
2. **Steps to Reproduce** - Exact steps to recreate the bug
3. **Expected vs. Actual Behavior**
4. **Impact** - How severe is the issue?
5. **Workaround** - Any temporary solutions?
6. **Related Files** - Where the bug might be located
7. **Date Reported**

## How to Document Resolved Bugs

When resolving a bug, move it to the Resolved Bugs section with:
1. **One-line description** - Succinct summary of the issue
2. **One-line solution** - Brief description of the fix
3. **Files Changed** - List of modified files
4. **Date Reported** - When the bug was first reported
5. **Resolution Date** - When the bug was fixed

Example:
```
### X. Bug title

**Status:** ✅ RESOLVED
**Description:** Brief one-line description of the issue.
**Solution:** Brief one-line description of the fix.
**Files Changed:** file1.ts, file2.tsx
**Date Reported:** YYYY-MM-DD
**Resolution Date:** YYYY-MM-DD
```
