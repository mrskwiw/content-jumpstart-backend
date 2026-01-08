# Phase 5: Code Quality Improvements

**Start Date:** January 7, 2026
**Target Completion:** January 21, 2026 (2 weeks)
**Status:** 🟡 Planning

---

## Overview

Phase 5 focuses on high-impact code quality improvements identified in the comprehensive audit. Priority is given to items that improve type safety, reduce duplication, and enhance error handling.

**Goal:** Improve codebase quality grade from B+ to A

---

## Priority 1: Type Safety (Week 1)

### 1.1 Python Type Hints (CRITICAL)
**Current:** 60% coverage
**Target:** 95% coverage
**Impact:** HIGH - Enables better IDE support, reduces runtime errors

**Files to Update:**
- `src/agents/content_generator.py` (1773 lines)
  - Lines 1083-1118: Add type hints to `_build_context()`
  - Lines 1120-1371: Replace `Any` with proper types in `_build_system_prompt()`
  - Lines 1405-1457: Fix Optional inconsistencies in `_infer_archetype()`

- `src/agents/coordinator.py` (557 lines)
  - Lines 237-282: Add return types to `_process_brief_input()`
  - Lines 283-322: Add type hints to `_fill_missing_fields()`

- `src/database/project_db.py` (1727 lines)
  - Add comprehensive type hints to all methods

**Approach:**
```python
from typing import Any, Dict, List, Optional, Union
from ..models.client_memory import ClientMemory

def _build_system_prompt(
    self,
    client_brief: ClientBrief,
    platform: Platform = Platform.LINKEDIN,
    client_memory: Optional[ClientMemory] = None,
) -> str:
    """Build system prompt with proper types"""
    # Implementation
```

**Verification:**
```bash
mypy src/ --strict --show-error-codes
```

**Estimated Effort:** 2 days

---

### 1.2 TypeScript Any Elimination (CRITICAL)
**Current:** 18 `any` violations
**Target:** 0 violations
**Impact:** HIGH - Prevents runtime type errors

**Files to Fix:**
1. **API Response Types (Priority 1)**
   - `api/auth.ts:6` - Add LoginResponse type
   - `api/clients.ts` - Add ClientResponse types
   - `api/projects.ts` - Add ProjectResponse types

2. **Error Handling (Priority 2)**
   - `components/ErrorBoundary.tsx:2` - Type error state properly

3. **Test Setup (Priority 3)**
   - `jest.setup.ts:3` - Type test mocks

**Example Fix:**
```typescript
// Before
export const authApi = {
  async login(credentials: LoginInput): Promise<any> {
    const { data } = await apiClient.post('/api/auth/login', credentials);
    return data;
  },
}

// After
interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export const authApi = {
  async login(credentials: LoginInput): Promise<LoginResponse> {
    const { data } = await apiClient.post<LoginResponse>('/api/auth/login', credentials);
    return data;
  },
}
```

**Verification:**
```bash
cd operator-dashboard && npm run lint -- --max-warnings 0
```

**Estimated Effort:** 1 day

---

## Priority 2: React Best Practices (Week 1)

### 2.1 Fix Purity Violations (CRITICAL)
**Issue:** Using Math.random() in render breaks hydration
**Files:** 3 files

**Files to Fix:**
- `components/ui/Input.tsx:32`
- `components/ui/Select.tsx:32`
- `components/ui/Textarea.tsx:34`

**Fix:**
```tsx
// Before
const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

// After (React 18+)
import { useId } from 'react';

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    // ...
  }
);
```

**Estimated Effort:** 30 minutes

---

### 2.2 Fix React Hook Dependencies (HIGH)
**Issue:** Missing dependencies cause stale closures
**Files:** 2 files

**Files to Fix:**
- `components/ui/AIAssistantSidebar.tsx:47`
- `pages/Wizard.tsx:148-161`

**Fix:**
```tsx
// Before
useEffect(() => {
  if (suggestions.length === 0) {
    loadContextSuggestions();
  }
}, []);

// After
const loadContextSuggestions = useCallback(async () => {
  // ... implementation
}, [/* dependencies */]);

useEffect(() => {
  if (suggestions.length === 0) {
    loadContextSuggestions();
  }
}, [suggestions.length, loadContextSuggestions]);
```

**Estimated Effort:** 1 hour

---

## Priority 3: Security Hardening (Week 1)

### 3.1 Fix Prompt Injection Sanitization Timing (HIGH)
**Issue:** Unsanitized brief passed to _generate_single_post
**File:** `src/agents/content_generator.py:596-607`

**Current Code:**
```python
def _generate_posts_from_quantities(...):
    sanitized_brief = self._sanitize_client_brief(client_brief)

    # ... 30 lines later ...

    post = self._generate_single_post(
        template=template,
        client_brief=client_brief,  # ❌ UNSANITIZED!
        ...
    )
```

**Fix:**
```python
post = self._generate_single_post(
    template=template,
    client_brief=sanitized_brief,  # ✓ Fixed
    ...
)
```

**Verification:** Review all calls to ensure sanitized brief is used consistently

**Estimated Effort:** 15 minutes

---

## Priority 4: Code Deduplication (Week 2)

### 4.1 Extract Research Agent Base Class (HIGH)
**Current:** 40% code duplication across 12 research tools
**Target:** <10% duplication
**Impact:** HIGH - Reduces ~2,000 lines of duplicate code

**Files Affected:**
- `src/research/audience_research.py` (659 lines)
- `src/research/competitive_analysis.py` (809 lines)
- `src/research/content_audit.py` (815 lines)
- `src/research/icp_workshop.py` (687 lines)
- `src/research/platform_strategy.py` (903 lines)
- `src/research/seo_keyword_research.py`
- `src/research/voice_analysis.py`
- ... 5 more

**Approach:**

1. **Create Base Class:**
```python
# src/research/base_research_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..utils.anthropic_client import AnthropicClient
from ..models.client_brief import ClientBrief

class BaseResearchAgent(ABC):
    """Abstract base class for all research agents"""

    def __init__(self, client: Optional[AnthropicClient] = None):
        from ..utils.anthropic_client import get_default_client
        self.client = client or get_default_client()
        self.validator = ResearchInputValidator()

    @property
    @abstractmethod
    def research_type(self) -> str:
        """Return research type name (e.g., 'ICP Workshop')"""
        pass

    async def run_research(
        self,
        client_brief: ClientBrief,
        **kwargs
    ) -> Dict[str, Any]:
        """Template method pattern for research workflow"""
        logger.info(f"Starting {self.research_type} research...")

        # Validate inputs
        self.validate_inputs({"business_description": client_brief.business_description, **kwargs})

        # Build prompts
        system_prompt = self.build_system_prompt()
        user_prompt = self.build_user_prompt(client_brief, **kwargs)

        # Execute research
        response = await self._execute_research(system_prompt, user_prompt)

        # Parse results
        result = self.parse_response(response)

        logger.info(f"{self.research_type} research complete")
        return result

    async def _execute_research(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Execute API call with retry logic"""
        response = await self.client.create_message_async(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=8000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate research-specific inputs"""
        pass

    @abstractmethod
    def build_system_prompt(self) -> str:
        """Build system prompt for this research type"""
        pass

    @abstractmethod
    def build_user_prompt(self, client_brief: ClientBrief, **kwargs) -> str:
        """Build user prompt for this research type"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse API response into structured data"""
        pass
```

2. **Update Individual Agents:**
```python
# src/research/icp_workshop.py (BEFORE: 687 lines)
class ICPWorkshop(BaseResearchAgent, CommonValidationMixin):
    """ICP Workshop Research Tool"""

    @property
    def research_type(self) -> str:
        return "ICP Workshop"

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        inputs["business_description"] = self.validate_business_description(inputs)
        # ... specific validations
        return True

    def build_system_prompt(self) -> str:
        return """You are an expert ICP (Ideal Customer Profile) strategist..."""

    def build_user_prompt(self, client_brief: ClientBrief, **kwargs) -> str:
        return f"""Business: {client_brief.business_description}..."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        # Parse structured ICP data
        return {"demographics": ..., "psychographics": ...}

# AFTER: ~250 lines (60% reduction!)
```

**Verification:**
```bash
# Run all research tool tests
pytest tests/unit/test_research_*.py -v

# Verify line count reduction
find src/research -name "*.py" -exec wc -l {} \; | awk '{s+=$1} END {print s}'
```

**Estimated Effort:** 3 days

---

## Priority 5: Error Handling Improvements (Week 2)

### 5.1 Granular Exception Handling (HIGH)
**Issue:** Broad `except Exception` catches too much
**File:** `backend/routers/generator.py:103`

**Current:**
```python
except Exception as e:
    logger.error(f"Background generation failed: {str(e)}")
    crud.update_run(db, run_id, status="failed", error_message=str(e))
```

**Fix:**
```python
except anthropic.RateLimitError as e:
    logger.warning(f"Rate limit hit for run {run_id}, will retry")
    crud.update_run(
        db, run_id,
        status="rate_limited",
        error_message="Rate limit exceeded. Will retry in 60 seconds.",
        retry_after=60
    )

except anthropic.APIError as e:
    logger.error(f"API error in run {run_id}: {e}")
    crud.update_run(
        db, run_id,
        status="failed",
        error_message=f"Anthropic API error: {str(e)}. Please try again."
    )

except ValidationError as e:
    logger.error(f"Validation error in run {run_id}: {e}")
    crud.update_run(
        db, run_id,
        status="failed",
        error_message=f"Brief validation failed: {str(e)}"
    )

except Exception as e:
    logger.error(f"Unexpected error in run {run_id}: {e}", exc_info=True)
    crud.update_run(
        db, run_id,
        status="failed",
        error_message=f"Unexpected error. Please contact support."
    )
```

**Estimated Effort:** 2 hours

---

### 5.2 Custom Exception Hierarchy (MEDIUM)
**Goal:** Create domain-specific exceptions for better error handling

**New File:** `src/exceptions/generation_exceptions.py`
```python
"""Custom exceptions for content generation"""

class BriefValidationError(ValueError):
    """Raised when client brief validation fails"""
    pass

class BriefProcessingError(Exception):
    """Raised when brief processing encounters issues"""
    pass

class GenerationError(Exception):
    """Base exception for content generation errors"""
    pass

class TemplateError(GenerationError):
    """Raised when template selection/loading fails"""
    pass

class QualityError(GenerationError):
    """Raised when quality validation fails"""
    pass
```

**Usage:**
```python
# In coordinator.py
try:
    client_brief = self.brief_parser.parse_brief(brief_text)
except Exception as e:
    raise BriefProcessingError(
        f"Could not parse brief: {str(e)}"
    ) from e
```

**Estimated Effort:** 1 day

---

## Priority 6: Cleanup & Maintenance (Week 2)

### 6.1 Remove Unused Imports/Variables
**Files:** 5 files identified

- `components/ui/AIAssistantSidebar.tsx:2` - Remove `MessageCircle`
- `components/deliverables/tabs/PostsTab.tsx:3` - Remove `Post`
- `components/wizard/ClientProfilePanel.tsx:14` - Prefix `_projectId`

**Estimated Effort:** 15 minutes

---

### 6.2 Fix Fast Refresh Violations
**Files:** 5 files

**Issue:** Exporting non-component constants breaks HMR

**Fix:**
```tsx
// Create separate file for non-component exports
// components/ui/button-variants.ts
export const buttonVariants = cva(...);

// components/ui/Button.tsx
import { buttonVariants } from './button-variants';
export { Button };  // Only export component
```

**Estimated Effort:** 30 minutes

---

## Success Metrics

### Type Safety
- [ ] Python type hints: 95%+ coverage
- [ ] TypeScript any types: 0 violations
- [ ] mypy --strict passes with 0 errors
- [ ] ESLint passes with 0 warnings

### Code Duplication
- [ ] Research agents: <10% duplication (from 40%)
- [ ] Total codebase: <15% duplication
- [ ] 2,000+ lines eliminated

### Code Quality Grade
- [ ] Overall: A (from B+)
- [ ] Python: A (from B)
- [ ] TypeScript: A- (from B-)

### Error Handling
- [ ] All background tasks use granular exception handling
- [ ] Custom exception hierarchy implemented
- [ ] All error messages user-friendly

---

## Testing Requirements

### Type Safety Tests
```bash
# Python type checking
mypy src/ --strict --show-error-codes

# TypeScript type checking
cd operator-dashboard && npm run type-check
```

### Research Agent Tests
```bash
# Verify all research agents still work after refactor
pytest tests/unit/test_research_*.py -v
pytest tests/integration/test_research_*.py -v
```

### Error Handling Tests
```bash
# Test error scenarios
pytest tests/unit/test_error_handling.py -v
```

---

## Implementation Timeline

### Week 1 (Jan 7-13)
- **Day 1-2:** Python type hints (content_generator.py, coordinator.py)
- **Day 3:** TypeScript any elimination
- **Day 4:** React purity violations + hook dependencies
- **Day 5:** Security fixes + error handling improvements

### Week 2 (Jan 14-20)
- **Day 1-3:** Research agent base class extraction
- **Day 4:** Custom exception hierarchy
- **Day 5:** Cleanup, testing, verification

### Completion Day (Jan 21)
- Documentation updates
- Code review
- Metrics verification
- Phase 5 completion report

---

## Risks & Mitigation

**Risk 1:** Type hint changes break existing code
- **Mitigation:** Run full test suite after each file
- **Mitigation:** Use `# type: ignore` temporarily for complex types

**Risk 2:** Research agent refactor introduces bugs
- **Mitigation:** Refactor one agent at a time
- **Mitigation:** Keep comprehensive test coverage
- **Mitigation:** Use feature flags for gradual rollout

**Risk 3:** Error handling changes affect user experience
- **Mitigation:** User-test error messages
- **Mitigation:** Ensure all errors have actionable guidance
- **Mitigation:** Add logging for monitoring

---

## Next Phase Preview: Phase 6

After Phase 5 completion, Phase 6 will focus on:
1. Medium-priority security enhancements (rate limiting, mass assignment)
2. Performance optimization (database query profiling, caching)
3. Test coverage expansion (target: 80%)
4. Long function refactoring (coordinator, content_generator)

---

**Status:** 🟡 Ready to begin
**Approval Needed:** Yes
**Estimated Total Effort:** 10 days (2 weeks with buffer)
