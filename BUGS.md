# Known Bugs

This file tracks known bugs and issues in the application.

## Active Bugs

(None)

---

## Resolved Bugs

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
