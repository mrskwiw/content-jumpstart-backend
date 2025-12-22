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
