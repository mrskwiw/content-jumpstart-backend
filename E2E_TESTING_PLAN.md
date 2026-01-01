# End-to-End Testing Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to implement automated end-to-end (e2e) testing for the Content Jumpstart Operator Dashboard using Playwright. The goal is to emulate real user interactions, catch regressions early, and ensure critical workflows function correctly across the entire stack.

## Why E2E Testing?

**Current Pain Points:**
- Manual testing of wizard flow takes 10-15 minutes per test cycle
- Regressions in multi-step workflows are hard to catch
- Integration issues between frontend and backend often discovered late
- No automated validation of critical user paths
- Screenshots of errors are reactive, not preventive

**Benefits of Automated E2E Testing:**
- ✅ **Catch bugs before deployment** - Automated tests run on every commit
- ✅ **Faster feedback loops** - Tests complete in 2-3 minutes vs 15 minutes manual
- ✅ **Regression prevention** - Ensure fixed bugs stay fixed
- ✅ **Documentation** - Tests serve as living documentation of user flows
- ✅ **Confidence in refactoring** - Make changes knowing tests will catch breaks
- ✅ **CI/CD integration** - Automated quality gates in deployment pipeline

## Technology Selection: Playwright

**Why Playwright over alternatives:**

| Feature | Playwright | Cypress | Puppeteer | Selenium |
|---------|-----------|---------|-----------|----------|
| TypeScript Support | ✅ Excellent | ✅ Good | ✅ Good | ⚠️ Limited |
| Multi-browser | ✅ Chrome, Firefox, Safari | ⚠️ Chrome only | ⚠️ Chrome only | ✅ All browsers |
| Auto-wait | ✅ Built-in | ✅ Built-in | ❌ Manual | ❌ Manual |
| Screenshot/Video | ✅ Built-in | ✅ Built-in | ⚠️ Limited | ⚠️ Limited |
| Network Intercept | ✅ Easy | ✅ Easy | ⚠️ Complex | ❌ Not supported |
| Codegen Tool | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Parallel Execution | ✅ Yes | ⚠️ Paid | ⚠️ Manual | ⚠️ Manual |
| CI/CD Ready | ✅ Excellent | ✅ Good | ✅ Good | ⚠️ Complex |

**Decision: Playwright** - Best overall package for React + TypeScript apps with modern features.

## Implementation Phases

### Phase 1: Setup & Infrastructure (Day 1)

**Goal:** Install Playwright and configure testing environment

**Tasks:**
1. Install Playwright in operator-dashboard project
2. Configure playwright.config.ts with test settings
3. Set up test directory structure
4. Create base fixtures and utilities
5. Add npm scripts for running tests

**Commands:**
```bash
cd operator-dashboard
npm install -D @playwright/test
npx playwright install
```

**Directory Structure:**
```
operator-dashboard/
├── tests/
│   ├── e2e/
│   │   ├── auth.spec.ts           # Login/logout tests
│   │   ├── wizard.spec.ts         # 5-step wizard flow
│   │   ├── projects.spec.ts       # Project management
│   │   ├── deliverables.spec.ts   # Deliverable tracking
│   │   └── settings.spec.ts       # Settings page
│   ├── fixtures/
│   │   ├── test-data.ts           # Mock client briefs, etc.
│   │   └── test-helpers.ts        # Shared utilities
│   └── setup/
│       ├── global-setup.ts        # Database seeding
│       └── global-teardown.ts     # Cleanup
├── playwright.config.ts
└── package.json
```

**Config (playwright.config.ts):**
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

**Deliverables:**
- ✅ Playwright installed and configured
- ✅ Test directory structure created
- ✅ npm scripts added: `npm run test:e2e`, `npm run test:e2e:ui`

---

### Phase 2: Authentication Tests (Day 2)

**Goal:** Test login, logout, and session management

**Test File: `tests/e2e/auth.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill login form
    await page.getByLabel('Email').fill('mrskwiw@gmail.com');
    await page.getByLabel('Password').fill('Random!1Pass');

    // Submit
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Verify redirect to dashboard
    await expect(page).toHaveURL('/');
    await expect(page.getByText('Welcome back')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel('Email').fill('wrong@example.com');
    await page.getByLabel('Password').fill('wrongpass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Verify error message
    await expect(page.getByText(/invalid credentials/i)).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByLabel('Email').fill('mrskwiw@gmail.com');
    await page.getByLabel('Password').fill('Random!1Pass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Logout
    await page.getByRole('button', { name: 'Logout' }).click();

    // Verify redirect to login
    await expect(page).toHaveURL('/login');
  });

  test('should persist session after refresh', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByLabel('Email').fill('mrskwiw@gmail.com');
    await page.getByLabel('Password').fill('Random!1Pass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Refresh page
    await page.reload();

    // Should still be logged in
    await expect(page).toHaveURL('/');
    await expect(page.getByText('Welcome back')).toBeVisible();
  });
});
```

**Deliverables:**
- ✅ 4 authentication test cases
- ✅ Tests verify login, logout, error handling, session persistence

---

### Phase 3: Wizard Flow Tests (Day 3-4)

**Goal:** Test complete 5-step wizard flow end-to-end

**Test File: `tests/e2e/wizard.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';
import { loginAsOperator } from '../fixtures/test-helpers';

test.describe('Wizard Flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/wizard');
  });

  test('should complete full wizard flow', async ({ page }) => {
    // Step 1: Client Profile
    await test.step('Fill client profile', async () => {
      await page.getByLabel('Company Name').fill('Test Company Inc');
      await page.getByLabel('Business Description').fill('We help B2B SaaS companies...');
      await page.getByLabel('Ideal Customer').fill('SaaS founders');
      await page.getByLabel('Main Problem Solved').fill('Lack of content strategy');

      // Add pain points
      await page.getByLabel('Pain Point').fill('No time to create content');
      await page.getByRole('button', { name: 'Add Pain Point' }).click();

      await page.getByRole('button', { name: 'Continue' }).click();
    });

    // Step 2: Template Selection
    await test.step('Select templates', async () => {
      // Wait for template grid to load
      await expect(page.getByText('Template #1')).toBeVisible();

      // Increase quantity for template 1 (Problem Recognition)
      const template1 = page.locator('[data-template-id="1"]');
      await template1.getByRole('button', { name: 'Increase quantity' }).click();
      await template1.getByRole('button', { name: 'Increase quantity' }).click();

      // Verify total posts updated
      await expect(page.getByText('Total Posts: 2')).toBeVisible();

      await page.getByRole('button', { name: 'Continue' }).click();
    });

    // Step 3: Research (optional - skip)
    await test.step('Skip research', async () => {
      await page.getByRole('button', { name: 'Skip Research' }).click();
    });

    // Step 4: Content Generation
    await test.step('Generate content', async () => {
      await page.getByRole('button', { name: 'Generate Posts' }).click();

      // Wait for generation to complete (max 2 minutes)
      await expect(page.getByText(/generation complete/i)).toBeVisible({ timeout: 120000 });

      // Verify posts generated
      await expect(page.getByText('2 posts generated')).toBeVisible();

      await page.getByRole('button', { name: 'Continue' }).click();
    });

    // Step 5: Review & Export
    await test.step('Review and export', async () => {
      // Verify deliverable preview
      await expect(page.getByText('Brand Voice Guide')).toBeVisible();
      await expect(page.getByText('30 Social Media Posts')).toBeVisible();

      // Download deliverable
      const downloadPromise = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Download Deliverable' }).click();
      const download = await downloadPromise;

      // Verify filename
      expect(download.suggestedFilename()).toMatch(/Test_Company_Inc.*\.docx/);
    });
  });

  test('should validate required fields in client profile', async ({ page }) => {
    await page.getByRole('button', { name: 'Continue' }).click();

    // Should show validation errors
    await expect(page.getByText(/company name is required/i)).toBeVisible();
    await expect(page.getByText(/business description is required/i)).toBeVisible();
  });

  test('should allow brief file import', async ({ page }) => {
    // Click import button
    await page.getByRole('button', { name: 'Import Client Brief' }).click();

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/sample_brief.txt');

    // Parse file
    await page.getByRole('button', { name: 'Upload and Parse' }).click();

    // Wait for preview modal
    await expect(page.getByText(/review imported data/i)).toBeVisible();

    // Confirm import
    await page.getByRole('button', { name: /import.*fields/i }).click();

    // Verify fields populated
    await expect(page.getByLabel('Company Name')).toHaveValue('Test Company Inc');
  });

  test('should prevent navigation with unsaved changes', async ({ page }) => {
    // Fill some fields
    await page.getByLabel('Company Name').fill('Unsaved Company');

    // Try to navigate away
    await page.getByRole('link', { name: 'Projects' }).click();

    // Should show confirmation dialog
    await expect(page.getByText(/unsaved changes/i)).toBeVisible();
  });
});
```

**Additional Test Cases:**
- Template quantity adjustments
- Custom topics input
- Include research checkbox
- Generation progress tracking
- Error handling during generation
- Navigation between wizard steps

**Deliverables:**
- ✅ Complete wizard flow test (happy path)
- ✅ Validation error tests
- ✅ Brief import test
- ✅ Unsaved changes warning test

---

### Phase 4: Projects & Deliverables Tests (Day 5)

**Goal:** Test project management and deliverable tracking

**Test File: `tests/e2e/projects.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';
import { loginAsOperator, createTestProject } from '../fixtures/test-helpers';

test.describe('Projects Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOperator(page);
  });

  test('should list all projects', async ({ page }) => {
    await page.goto('/projects');

    // Verify project cards displayed
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
    await expect(page.locator('[data-testid="project-card"]')).toHaveCount(3); // Assuming 3 test projects
  });

  test('should filter projects by status', async ({ page }) => {
    await page.goto('/projects');

    // Filter by "In Progress"
    await page.getByRole('button', { name: 'Filter' }).click();
    await page.getByRole('checkbox', { name: 'In Progress' }).check();

    // Verify filtered results
    await expect(page.locator('[data-testid="project-card"]')).toHaveCount(1);
  });

  test('should search projects by name', async ({ page }) => {
    await page.goto('/projects');

    await page.getByPlaceholder('Search projects...').fill('Acme Corp');

    // Verify search results
    await expect(page.getByText('Acme Corp')).toBeVisible();
    await expect(page.locator('[data-testid="project-card"]')).toHaveCount(1);
  });

  test('should view project details', async ({ page }) => {
    await page.goto('/projects');

    // Click first project
    await page.getByText('Acme Corp').click();

    // Verify details page
    await expect(page).toHaveURL(/\/projects\/project-\d+/);
    await expect(page.getByRole('heading', { name: 'Acme Corp' })).toBeVisible();
    await expect(page.getByText('30 posts')).toBeVisible();
  });
});

test.describe('Deliverables Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/deliverables');
  });

  test('should mark deliverable as delivered', async ({ page }) => {
    // Click "Mark Delivered" button
    await page.getByRole('button', { name: 'Mark Delivered' }).first().click();

    // Fill delivery modal
    await page.getByLabel('Proof URL').fill('https://example.com/proof');
    await page.getByLabel('Delivery Notes').fill('Sent via email');
    await page.getByRole('button', { name: 'Confirm' }).click();

    // Verify status updated
    await expect(page.getByText('Delivered')).toBeVisible();
  });

  test('should handle deliverable details error gracefully', async ({ page }) => {
    // This tests the bug from the error screenshot
    await page.getByText('deliv-1').click();

    // Should not show JSON validation error
    await expect(page.getByText(/Invalid ISO datetime/i)).not.toBeVisible();

    // Should show user-friendly error or load details correctly
    await expect(
      page.getByText(/error loading/i).or(page.getByText('Created'))
    ).toBeVisible();
  });
});
```

**Deliverables:**
- ✅ Project listing, filtering, search tests
- ✅ Deliverable status update tests
- ✅ Error handling tests (datetime validation bug)

---

### Phase 5: API Mocking & Error Scenarios (Day 6)

**Goal:** Test error handling, loading states, and edge cases

**Test File: `tests/e2e/error-scenarios.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';
import { loginAsOperator } from '../fixtures/test-helpers';

test.describe('Error Scenarios', () => {
  test('should handle API timeout during generation', async ({ page }) => {
    await loginAsOperator(page);

    // Mock slow API response
    await page.route('**/api/generator/generate', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 35000)); // 35s timeout
      await route.fulfill({ status: 504, body: 'Gateway Timeout' });
    });

    await page.goto('/wizard');
    // ... complete wizard steps ...
    await page.getByRole('button', { name: 'Generate Posts' }).click();

    // Should show timeout error
    await expect(page.getByText(/request timed out/i)).toBeVisible();

    // Should allow retry
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  });

  test('should handle network disconnection', async ({ page, context }) => {
    await loginAsOperator(page);

    // Simulate offline
    await context.setOffline(true);

    await page.goto('/wizard');
    await page.getByRole('button', { name: 'Continue' }).click();

    // Should show network error
    await expect(page.getByText(/network error/i)).toBeVisible();
  });

  test('should handle invalid brief file upload', async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/wizard');

    await page.getByRole('button', { name: 'Import Client Brief' }).click();

    // Upload invalid file type
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/invalid.pdf');

    // Should show validation error
    await expect(page.getByText(/only .txt and .md files/i)).toBeVisible();
  });

  test('should handle SQLAlchemy session errors', async ({ page }) => {
    await loginAsOperator(page);

    // Mock session error
    await page.route('**/api/projects', async (route) => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({
          detail: {
            code: 'DATABASE_ERROR',
            message: 'SQLAlchemy session error'
          }
        })
      });
    });

    await page.goto('/projects');

    // Should show user-friendly error, not technical details
    await expect(page.getByText(/unable to load projects/i)).toBeVisible();
    await expect(page.getByText(/sqlalchemy/i)).not.toBeVisible();
  });
});
```

**Deliverables:**
- ✅ API timeout handling
- ✅ Network error handling
- ✅ File upload validation
- ✅ Database error graceful degradation

---

### Phase 6: Visual Regression Testing (Day 7)

**Goal:** Detect unintended UI changes

**Test File: `tests/e2e/visual-regression.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';
import { loginAsOperator } from '../fixtures/test-helpers';

test.describe('Visual Regression', () => {
  test('wizard step 1 - client profile', async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/wizard');

    // Take screenshot
    await expect(page).toHaveScreenshot('wizard-step-1.png');
  });

  test('wizard step 2 - template selection', async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/wizard');

    // Fill step 1 and continue
    await page.getByLabel('Company Name').fill('Test');
    await page.getByLabel('Business Description').fill('Test desc');
    await page.getByLabel('Ideal Customer').fill('Test customer');
    await page.getByLabel('Main Problem Solved').fill('Test problem');
    await page.getByRole('button', { name: 'Continue' }).click();

    // Take screenshot
    await expect(page).toHaveScreenshot('wizard-step-2.png');
  });

  test('projects page - grid view', async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/projects');

    await expect(page).toHaveScreenshot('projects-grid.png');
  });

  test('deliverables page - list view', async ({ page }) => {
    await loginAsOperator(page);
    await page.goto('/deliverables');

    await expect(page).toHaveScreenshot('deliverables-list.png');
  });
});
```

**Deliverables:**
- ✅ Screenshot baselines for key pages
- ✅ Automatic visual diff detection

---

### Phase 7: CI/CD Integration (Day 8)

**Goal:** Automate tests in GitHub Actions

**GitHub Workflow: `.github/workflows/e2e-tests.yml`**

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    timeout-minutes: 60
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: content_jumpstart_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: operator-dashboard/package-lock.json

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install backend dependencies
        run: |
          cd project
          pip install -r requirements.txt

      - name: Install frontend dependencies
        run: |
          cd project/operator-dashboard
          npm ci

      - name: Install Playwright Browsers
        run: |
          cd project/operator-dashboard
          npx playwright install --with-deps

      - name: Run database migrations
        run: |
          cd project/backend
          alembic upgrade head
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/content_jumpstart_test

      - name: Seed test data
        run: |
          cd project
          python tests/setup/seed_test_data.py
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/content_jumpstart_test

      - name: Start backend server
        run: |
          cd project/backend
          uvicorn main:app --host 0.0.0.0 --port 8000 &
          sleep 5
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/content_jumpstart_test
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Run Playwright tests
        run: |
          cd project/operator-dashboard
          npx playwright test
        env:
          VITE_API_URL: http://localhost:8000

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: project/operator-dashboard/playwright-report/
          retention-days: 30

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: project/operator-dashboard/test-results/
          retention-days: 30
```

**Deliverables:**
- ✅ GitHub Actions workflow configured
- ✅ Tests run on every PR and push
- ✅ Test reports uploaded as artifacts
- ✅ Database seeding for consistent test data

---

## Test Helpers & Fixtures

**File: `tests/fixtures/test-helpers.ts`**

```typescript
import { Page } from '@playwright/test';

export async function loginAsOperator(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill('mrskwiw@gmail.com');
  await page.getByLabel('Password').fill('Random!1Pass');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL('/');
}

export async function createTestProject(page: Page, projectName: string) {
  await page.goto('/wizard');

  // Fill client profile
  await page.getByLabel('Company Name').fill(projectName);
  await page.getByLabel('Business Description').fill('Test company description');
  await page.getByLabel('Ideal Customer').fill('Test customers');
  await page.getByLabel('Main Problem Solved').fill('Test problem');
  await page.getByRole('button', { name: 'Continue' }).click();

  // Select templates
  const template1 = page.locator('[data-template-id="1"]');
  await template1.getByRole('button', { name: 'Increase quantity' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();

  // Skip research
  await page.getByRole('button', { name: 'Skip Research' }).click();

  return page;
}

export async function waitForGeneration(page: Page, timeout = 120000) {
  await page.waitForSelector('[data-testid="generation-complete"]', { timeout });
}
```

**File: `tests/fixtures/test-data.ts`**

```typescript
export const testClientBrief = {
  companyName: 'Test Company Inc',
  businessDescription: 'We help B2B SaaS companies grow through content marketing',
  idealCustomer: 'SaaS founders and marketing leaders',
  mainProblemSolved: 'Lack of consistent content strategy',
  painPoints: [
    'No time to create content',
    'Struggling with content ideas',
    'Low engagement on social media'
  ],
  platforms: ['LinkedIn', 'Twitter'],
  tonePreference: 'Professional but approachable'
};

export const testBriefFile = `
Company Name: Test Company Inc
Business Description: We help B2B SaaS companies grow through content marketing
Ideal Customer: SaaS founders and marketing leaders
Main Problem Solved: Lack of consistent content strategy

Pain Points:
- No time to create content
- Struggling with content ideas
- Low engagement on social media

Platforms: LinkedIn, Twitter
Tone: Professional but approachable
`;
```

---

## Success Metrics

**Test Coverage Goals:**
- ✅ **80%+ coverage** of critical user paths
- ✅ **100% coverage** of wizard flow (all 5 steps)
- ✅ **All bugs from error screenshots** have regression tests
- ✅ **<5 minutes** total test execution time

**Quality Gates:**
- ✅ All tests must pass before merge to main
- ✅ Visual regression tests must pass or be explicitly approved
- ✅ No flaky tests (tests must pass 3 consecutive times)
- ✅ Test reports generated and accessible

**Maintenance:**
- ✅ Tests updated when features change
- ✅ Screenshots updated when UI intentionally changes
- ✅ Test data refreshed monthly

---

## Implementation Timeline

| Phase | Days | Deliverables |
|-------|------|--------------|
| 1. Setup & Infrastructure | 1 | Playwright configured, directory structure |
| 2. Authentication Tests | 1 | Login/logout/session tests |
| 3. Wizard Flow Tests | 2 | Complete wizard e2e tests |
| 4. Projects & Deliverables | 1 | Management interface tests |
| 5. Error Scenarios | 1 | API mocking, error handling |
| 6. Visual Regression | 1 | Screenshot baseline tests |
| 7. CI/CD Integration | 1 | GitHub Actions workflow |
| **Total** | **8 days** | **Full e2e test suite** |

---

## Running Tests Locally

```bash
# Install dependencies
cd operator-dashboard
npm install

# Install Playwright browsers
npx playwright install

# Run all tests
npm run test:e2e

# Run tests with UI (interactive mode)
npm run test:e2e:ui

# Run specific test file
npx playwright test tests/e2e/wizard.spec.ts

# Debug a test
npx playwright test --debug

# Update visual snapshots
npx playwright test --update-snapshots

# View test report
npx playwright show-report
```

---

## Best Practices

**1. Use Semantic Selectors**
```typescript
// ✅ Good - semantic, stable
await page.getByRole('button', { name: 'Continue' })
await page.getByLabel('Company Name')
await page.getByText('Welcome back')

// ❌ Bad - brittle, implementation-dependent
await page.locator('.btn-primary')
await page.locator('#input-123')
await page.locator('div > div > button')
```

**2. Wait for Actions to Complete**
```typescript
// ✅ Good - explicit wait
await page.getByRole('button', { name: 'Submit' }).click();
await page.waitForResponse(resp => resp.url().includes('/api/') && resp.status() === 200);

// ❌ Bad - race conditions
await page.getByRole('button', { name: 'Submit' }).click();
await page.locator('.success-message'); // Might not appear yet
```

**3. Use test.step() for Complex Flows**
```typescript
test('wizard flow', async ({ page }) => {
  await test.step('Login', async () => {
    // Login steps
  });

  await test.step('Fill client profile', async () => {
    // Profile steps
  });

  await test.step('Generate content', async () => {
    // Generation steps
  });
});
```

**4. Isolate Tests**
```typescript
// ✅ Good - each test is independent
test.beforeEach(async ({ page }) => {
  await loginAsOperator(page);
  await createFreshTestData();
});

test.afterEach(async () => {
  await cleanupTestData();
});

// ❌ Bad - tests depend on each other
test('create project', async ({ page }) => {
  // Creates project-123
});

test('edit project', async ({ page }) => {
  // Assumes project-123 exists
});
```

---

## Troubleshooting

**Common Issues:**

1. **Tests timeout**
   - Increase timeout: `{ timeout: 60000 }`
   - Check if backend is running
   - Verify network connectivity

2. **Flaky tests**
   - Add explicit waits: `await page.waitForLoadState('networkidle')`
   - Use `toBeVisible()` instead of `toHaveCount()`
   - Disable animations: `page.emulateMedia({ reducedMotion: 'reduce' })`

3. **Screenshots don't match**
   - Fonts might differ across OS
   - Use `threshold` option: `await expect(page).toHaveScreenshot({ threshold: 0.2 })`
   - Run tests in Docker for consistency

---

## Next Steps After Implementation

1. **Add Performance Tests** - Measure page load times, generation speed
2. **Add Accessibility Tests** - Verify WCAG compliance with axe-core
3. **Mobile Testing** - Test responsive layouts on mobile devices
4. **Load Testing** - Simulate multiple concurrent users
5. **Security Testing** - Test XSS, CSRF, SQL injection prevention

---

## Conclusion

This plan provides a comprehensive roadmap for implementing automated e2e testing with Playwright. The tests will:
- ✅ Catch bugs before they reach production
- ✅ Provide confidence in refactoring and feature development
- ✅ Serve as living documentation of user workflows
- ✅ Integrate seamlessly with CI/CD pipeline

**Estimated ROI:**
- **Time saved:** 10-15 min manual testing → 3 min automated testing per run
- **Bug detection:** Catch regressions immediately vs days/weeks later
- **Developer confidence:** Make changes knowing tests will catch breaks
- **Quality improvement:** Consistent testing of all critical paths

**Start with:** Phase 1-3 (Setup, Auth, Wizard) for immediate value, then expand to remaining phases.
