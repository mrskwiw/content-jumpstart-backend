# Known Bugs

This file tracks known bugs and issues in the application.

## Active Bugs

### 1. System-wide camelCase/snake_case misalignment investigation needed

**Status:** Open - Investigation Required
**Severity:** Medium
**Component:** Backend API schemas
**Location:** `backend/schemas/*.py`

**Description:**
The Wizard bug (#1 in Resolved) revealed a field naming mismatch between frontend (camelCase) and backend (snake_case). This issue likely exists in other schemas across the system.

**Issue:**
- Frontend TypeScript uses camelCase conventions (`clientId`, `createdAt`, etc.)
- Backend Python/Pydantic uses snake_case conventions (`client_id`, `created_at`, etc.)
- Some schemas have `populate_by_name=True` configuration, but others don't
- This creates inconsistent API behavior and potential validation failures

**Required Action:**
Systematic audit of all backend schemas to ensure consistent field name handling:

1. **Audit all schema files:**
   - `backend/schemas/project.py` ✅ (fixed)
   - `backend/schemas/client.py`
   - `backend/schemas/brief.py`
   - `backend/schemas/deliverable.py`
   - `backend/schemas/post.py`
   - `backend/schemas/run.py`
   - `backend/schemas/auth.py`
   - Any other schema files

2. **Check each schema for:**
   - Input schemas (Create/Update) that need `populate_by_name=True`
   - Response schemas that need `alias_generator` for camelCase output
   - Consistency in configuration across all schemas

3. **Test each API endpoint:**
   - Verify frontend can send camelCase
   - Verify backend returns camelCase
   - Check for any validation errors

**Impact:**
- Potential hidden bugs in other API endpoints
- Inconsistent API behavior across endpoints
- Future developer confusion about field naming conventions

**Priority:**
Medium - Should be investigated soon to prevent future bugs, but not blocking current functionality

**Related Files:**
- All files in `backend/schemas/`
- `operator-dashboard/src/api/*.ts` (frontend API interfaces)

**Date Reported:** December 21, 2025

---

## Resolved Bugs

### 1. Wizard fails to create project after creating client

**Status:** ✅ RESOLVED
**Severity:** High
**Component:** Wizard (operator-dashboard)
**Location:** `backend/schemas/project.py`

**Description:**
When using the wizard to create a new client:
1. Client is created successfully
2. Wizard then fails to advance to the next step
3. Error message displayed: "Failed to create project"

**Root Cause:**
Field naming mismatch between frontend and backend:
- Frontend sends `clientId` (camelCase) in CreateProjectInput
- Backend ProjectCreate schema expects `client_id` (snake_case)
- ProjectResponse schema had `populate_by_name=True` to accept both formats, but ProjectBase/ProjectCreate didn't

**Solution:**
Added `model_config = ConfigDict(populate_by_name=True)` to ProjectBase class in `backend/schemas/project.py`.

This allows Pydantic to accept both camelCase (`clientId`) and snake_case (`client_id`) field names during validation.

**Files Changed:**
- `backend/schemas/project.py` - Added ConfigDict to ProjectBase

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
