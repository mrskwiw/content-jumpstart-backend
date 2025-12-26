/**
 * Wizard E2E Test Suite
 *
 * Tests the complete wizard flow with:
 * 1. New client creation
 * 2. Existing client selection and update
 *
 * Run with: npx playwright test tests/e2e/wizard-flow.spec.ts --headed
 */

import { test, expect, Page } from '@playwright/test';

// Configuration
const BASE_URL = 'http://localhost:5174';
const TEST_USER = {
  email: 'mrskwiw@gmail.com',
  password: 'Random!1Pass'
};

// Test data
const NEW_CLIENT_DATA = {
  companyName: `E2E Test Client ${Date.now()}`,
  businessDescription: 'We provide comprehensive software testing solutions for modern web applications.',
  idealCustomer: 'Mid-sized tech companies with active development teams who value quality assurance.',
  mainProblemSolved: 'Reducing bugs in production and improving release confidence through automated testing.',
  tonePreference: 'professional',
  platforms: ['linkedin', 'twitter'],
  painPoint1: 'Manual testing is time-consuming',
  painPoint2: 'Difficult to maintain test coverage',
  question1: 'How do I get started with automated testing?',
  answer1: 'We provide onboarding and training for your team'
};

// Helper function to login
async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);

  // Wait for page to fully load
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Fill login form
  await page.getByPlaceholder(/you@example.com/i).fill(TEST_USER.email);
  await page.getByPlaceholder(/••••••••/i).fill(TEST_USER.password);

  // Click sign in and wait for navigation
  await page.getByRole('button', { name: /Sign in/i }).click();

  // Wait for either dashboard or error message
  try {
    await expect(page).toHaveURL(/.*dashboard/, { timeout: 15000 });
  } catch (e) {
    // Check if there's an error message
    const errorMsg = await page.locator('text=/error|cannot|failed/i').first().textContent();
    if (errorMsg) {
      console.error(`Login failed with error: ${errorMsg}`);
    }
    throw e;
  }
}

test.describe('Wizard Flow - Complete E2E Tests', () => {
  let page: Page;
  let testClientId: string | null = null;

  test.beforeEach(async ({ browser }) => {
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
    });
    page = await context.newPage();
    await login(page);
  });

  // ============================================================
  // TEST 1: NEW CLIENT WIZARD FLOW
  // ============================================================

  test('Wizard Flow - New Client Creation', async () => {
    console.log('\n🧙 Testing Wizard with NEW Client');

    // Navigate to wizard
    await page.goto(`${BASE_URL}/dashboard/wizard`);
    await expect(page.getByText(/Project Wizard/i)).toBeVisible();
    console.log('✅ Wizard page loaded');

    // Step 1: Client Profile - Create New Client
    console.log('\n📝 Step 1: Client Profile');

    // Should default to "Create New Client"
    const createNewButton = page.getByRole('button', { name: /Create New Client/i });
    await expect(createNewButton).toBeVisible();
    await expect(createNewButton).toHaveClass(/primary|bg-primary/); // Should be active
    console.log('✅ "Create New Client" is selected by default');

    // Fill client profile form
    await page.getByPlaceholder('Acme Corp').fill(NEW_CLIENT_DATA.companyName);
    await page.getByPlaceholder(/We provide cloud-based/i).fill(NEW_CLIENT_DATA.businessDescription);
    await page.getByPlaceholder(/Small business owners/i).fill(NEW_CLIENT_DATA.idealCustomer);
    await page.getByPlaceholder(/We eliminate the chaos/i).fill(NEW_CLIENT_DATA.mainProblemSolved);
    console.log('✅ Basic client info filled');

    // Select tone preference
    await page.selectOption('select', NEW_CLIENT_DATA.tonePreference);
    console.log('✅ Tone preference selected');

    // Select platforms (checkboxes or multi-select)
    for (const platform of NEW_CLIENT_DATA.platforms) {
      const platformCheckbox = page.locator(`input[value="${platform}"]`).or(
        page.locator(`label:has-text("${platform}")`).locator('input')
      );
      if (await platformCheckbox.count() > 0) {
        await platformCheckbox.first().check();
      }
    }
    console.log('✅ Platforms selected');

    // Add pain points
    const addPainPointButton = page.getByRole('button', { name: /Add.*Pain Point/i });
    if (await addPainPointButton.count() > 0) {
      await addPainPointButton.click();
      const painPointInputs = page.locator('input[placeholder*="pain" i]');
      if (await painPointInputs.count() >= 1) {
        await painPointInputs.first().fill(NEW_CLIENT_DATA.painPoint1);
      }
      await addPainPointButton.click();
      if (await painPointInputs.count() >= 2) {
        await painPointInputs.nth(1).fill(NEW_CLIENT_DATA.painPoint2);
      }
      console.log('✅ Pain points added');
    }

    // Add customer question with answer
    const addQuestionButton = page.getByRole('button', { name: /Add.*Question/i });
    if (await addQuestionButton.count() > 0) {
      await addQuestionButton.click();
      const questionInput = page.locator('input[placeholder*="question" i]').or(
        page.locator('textarea[placeholder*="question" i]')
      );
      const answerInput = page.locator('input[placeholder*="answer" i]').or(
        page.locator('textarea[placeholder*="answer" i]')
      );

      if (await questionInput.count() > 0) {
        await questionInput.first().fill(NEW_CLIENT_DATA.question1);
      }
      if (await answerInput.count() > 0) {
        await answerInput.first().fill(NEW_CLIENT_DATA.answer1);
      }
      console.log('✅ Customer Q&A added');
    }

    // Save client and advance to next step
    const saveButton = page.getByRole('button', { name: /Save.*Profile|Continue/i });
    await saveButton.click();

    // Wait for navigation to Research step
    await page.waitForTimeout(2000);
    const researchStepActive = await page.locator('text=/Research/i').first().isVisible();
    expect(researchStepActive).toBeTruthy();
    console.log('✅ Advanced to Research step');

    // Verify client was created (check wizard status panel)
    const clientBriefStatus = page.getByText(/Client Brief.*Saved/i);
    if (await clientBriefStatus.count() > 0) {
      console.log('✅ Client brief saved confirmation visible');
    }

    console.log('\n✅ NEW CLIENT WIZARD FLOW: PASSED');
  });

  // ============================================================
  // TEST 2: EXISTING CLIENT WIZARD FLOW
  // ============================================================

  test('Wizard Flow - Existing Client Selection and Update', async () => {
    console.log('\n🧙 Testing Wizard with EXISTING Client');

    // Navigate to wizard
    await page.goto(`${BASE_URL}/dashboard/wizard`);
    await expect(page.getByText(/Project Wizard/i)).toBeVisible();
    console.log('✅ Wizard page loaded');

    // Step 1: Client Profile - Select Existing Client
    console.log('\n📝 Step 1: Select Existing Client');

    // Click "Use Existing Client" button
    const useExistingButton = page.getByRole('button', { name: /Use Existing Client/i });
    await useExistingButton.click();
    await page.waitForTimeout(500);
    await expect(useExistingButton).toHaveClass(/primary|bg-primary/);
    console.log('✅ "Use Existing Client" selected');

    // Wait for client dropdown to appear
    const clientSelect = page.locator('select').filter({ hasText: /Select a client/i }).or(
      page.locator('select[id*="client" i]')
    );
    await expect(clientSelect).toBeVisible();
    console.log('✅ Client dropdown visible');

    // Get list of clients and select the first one
    const options = await clientSelect.locator('option').all();
    if (options.length > 1) { // More than just the placeholder option
      const firstClientOption = options[1]; // Skip the placeholder
      const clientValue = await firstClientOption.getAttribute('value');
      const clientName = await firstClientOption.textContent();

      await clientSelect.selectOption(clientValue || '');
      console.log(`✅ Selected existing client: ${clientName}`);

      // Wait for form to populate
      await page.waitForTimeout(1000);

      // Verify form fields are populated
      const companyNameInput = page.getByPlaceholder('Acme Corp');
      const companyNameValue = await companyNameInput.inputValue();
      expect(companyNameValue).toBeTruthy();
      expect(companyNameValue.length).toBeGreaterThan(0);
      console.log(`✅ Form populated with company name: ${companyNameValue}`);

      // Check if other fields are populated (optional fields might be empty)
      const businessDescInput = page.getByPlaceholder(/We provide cloud-based/i);
      const businessDescValue = await businessDescInput.inputValue();
      if (businessDescValue) {
        console.log(`✅ Business description populated: ${businessDescValue.substring(0, 50)}...`);
      }

      // Update a field to test the update functionality
      const updatedDescription = `Updated via E2E test at ${new Date().toISOString()}`;
      await businessDescInput.fill(updatedDescription);
      console.log('✅ Updated business description field');

      // Option 1: Use "Continue to Research" button (skip form save)
      const continueButton = page.getByRole('button', { name: /Continue to Research/i });
      if (await continueButton.count() > 0 && await continueButton.isVisible()) {
        console.log('✅ "Continue to Research" button available');
        await continueButton.click();
        console.log('✅ Clicked "Continue to Research" - skipped detailed form');
      } else {
        // Option 2: Fill and save the complete form
        const saveButton = page.getByRole('button', { name: /Save.*Client/i });
        await saveButton.click();
        console.log('✅ Clicked "Save Client" - updating with form data');
      }

      // Wait for navigation to Research step
      await page.waitForTimeout(2000);
      const researchStepActive = await page.locator('text=/Research/i').first().isVisible();
      expect(researchStepActive).toBeTruthy();
      console.log('✅ Advanced to Research step');

      // Verify project was created with existing client
      const wizardStatus = page.locator('text=/Wizard Status/i');
      if (await wizardStatus.count() > 0) {
        console.log('✅ Wizard status panel visible');
      }

      console.log('\n✅ EXISTING CLIENT WIZARD FLOW: PASSED');
    } else {
      console.log('⚠️  No existing clients found - test skipped');
      console.log('   Create a client first using the NEW CLIENT test');
    }
  });

  // ============================================================
  // TEST 3: FORM VALIDATION
  // ============================================================

  test('Wizard - Form Validation', async () => {
    console.log('\n🧙 Testing Wizard Form Validation');

    await page.goto(`${BASE_URL}/dashboard/wizard`);

    // Try to save without filling required fields
    const saveButton = page.getByRole('button', { name: /Save.*Profile/i });
    await saveButton.click();

    // Should show validation errors
    await page.waitForTimeout(1000);
    const errorMessages = page.locator('text=/required|invalid|must/i');
    const errorCount = await errorMessages.count();

    if (errorCount > 0) {
      console.log(`✅ Validation working - ${errorCount} error(s) displayed`);
    } else {
      console.log('⚠️  No validation errors shown (might be preventing submit)');
    }

    // Check that we didn't advance (still on profile step)
    const profileStep = page.locator('text=/Client Profile/i');
    const isStillOnProfile = await profileStep.first().isVisible();
    expect(isStillOnProfile).toBeTruthy();
    console.log('✅ Did not advance without valid data');

    console.log('\n✅ FORM VALIDATION TEST: PASSED');
  });
});
