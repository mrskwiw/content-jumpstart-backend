/**
 * Minimal Wizard Test - Verify only company name is required
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
  await page.getByPlaceholder(/you@example.com/i).fill(TEST_USER.email);
  await page.getByPlaceholder(/••••••••/i).fill(TEST_USER.password);
  await page.getByRole('button', { name: /Sign in/i }).click();
  await expect(page).toHaveURL(/.*dashboard/, { timeout: 15000 });
}

test('Wizard - Minimal Required Fields (Company Name Only)', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  await login(page);

  // Navigate to wizard
  await page.goto(`${BASE_URL}/dashboard/wizard`);
  await expect(page.getByText(/Project Wizard/i)).toBeVisible();
  console.log('✅ Wizard page loaded');

  // Fill ONLY company name
  const companyName = `Minimal Test ${Date.now()}`;
  await page.getByPlaceholder('Acme Corp').fill(companyName);
  console.log(`✅ Filled company name: ${companyName}`);

  // Try to save with only company name
  const saveButton = page.getByRole('button', { name: /Save.*Profile/i });
  await saveButton.click();

  // Should advance to Research step
  await page.waitForTimeout(2000);
  const researchStepActive = await page.locator('text=/Research/i').first().isVisible();
  expect(researchStepActive).toBeTruthy();
  console.log('✅ Advanced to Research with only company name filled');

  console.log('\n✅ MINIMAL VALIDATION TEST: PASSED');
});
