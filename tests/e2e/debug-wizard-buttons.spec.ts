/**
 * Debug Wizard Buttons - Step-by-step with screenshots
 */
import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:5174';
const TEST_USER = {
  email: 'mrskwiw@gmail.com',
  password: 'Random!1Pass'
};

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'tests/debug/01-login-page.png', fullPage: true });

  await page.getByPlaceholder(/you@example.com/i).fill(TEST_USER.email);
  await page.getByPlaceholder(/••••••••/i).fill(TEST_USER.password);
  await page.screenshot({ path: 'tests/debug/02-login-filled.png', fullPage: true });

  await page.getByRole('button', { name: /Sign in/i }).click();
  await page.waitForURL(/.*dashboard/, { timeout: 15000 });
  await page.screenshot({ path: 'tests/debug/03-dashboard.png', fullPage: true });
}

test('Debug Wizard Buttons', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // Step 1: Login
  await login(page);
  console.log('✅ Step 1: Logged in');

  // Step 2: Navigate to wizard
  await page.goto(`${BASE_URL}/dashboard/wizard`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'tests/debug/04-wizard-initial.png', fullPage: true });
  console.log('✅ Step 2: Wizard page loaded');

  // Step 3: Check initial state
  const createNewButton = page.getByRole('button', { name: /Create New Client/i });
  const isCreateNewVisible = await createNewButton.isVisible();
  console.log(`Create New Client button visible: ${isCreateNewVisible}`);

  // Step 4: Fill only company name
  const companyName = `Debug Test ${Date.now()}`;
  await page.getByPlaceholder('Acme Corp').fill(companyName);
  await page.screenshot({ path: 'tests/debug/05-company-filled.png', fullPage: true });
  console.log(`✅ Step 4: Filled company name: ${companyName}`);

  // Step 5: Find and examine Save Profile button
  const saveButton = page.getByRole('button', { name: /Save.*Profile/i });
  const isSaveButtonVisible = await saveButton.isVisible();
  const isSaveButtonEnabled = await saveButton.isEnabled();
  const saveButtonText = await saveButton.textContent();

  console.log(`Save Profile button visible: ${isSaveButtonVisible}`);
  console.log(`Save Profile button enabled: ${isSaveButtonEnabled}`);
  console.log(`Save Profile button text: "${saveButtonText}"`);

  await page.screenshot({ path: 'tests/debug/06-before-save.png', fullPage: true });

  // Step 6: Click Save Profile and monitor
  console.log('⏳ Clicking Save Profile button...');

  // Set up console listener to catch any errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`❌ Browser console error: ${msg.text()}`);
    }
  });

  // Set up request listener to see API calls
  page.on('request', request => {
    if (request.url().includes('/api/')) {
      console.log(`📤 API Request: ${request.method()} ${request.url()}`);
    }
  });

  page.on('response', async response => {
    if (response.url().includes('/api/')) {
      console.log(`📥 API Response: ${response.status()} ${response.url()}`);
      if (response.status() >= 400) {
        const body = await response.text();
        console.log(`❌ Error response body: ${body}`);
      }
    }
  });

  await saveButton.click();

  // Step 7: Wait and check what happened
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'tests/debug/07-after-save-click.png', fullPage: true });

  // Check current URL
  const currentUrl = page.url();
  console.log(`Current URL: ${currentUrl}`);

  // Check if we advanced to Research step
  const researchStepVisible = await page.locator('text=/Research/i').first().isVisible();
  console.log(`Research step visible: ${researchStepVisible}`);

  // Check for any error messages
  const errorMessages = await page.locator('text=/error|failed|unable/i').all();
  console.log(`Found ${errorMessages.length} error message(s)`);
  for (const error of errorMessages) {
    const errorText = await error.textContent();
    console.log(`  ❌ Error: ${errorText}`);
  }

  // Final screenshot
  await page.screenshot({ path: 'tests/debug/08-final-state.png', fullPage: true });

  console.log('\n📊 Debug session complete. Check tests/debug/ for screenshots.');
});
