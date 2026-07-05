/**
 * Test Overview Page Authentication
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

test('Overview Page - Check API Authentication', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // Setup API monitoring
  const apiCalls: { url: string; status: number; method: string }[] = [];

  page.on('response', async response => {
    if (response.url().includes('/api/')) {
      apiCalls.push({
        url: response.url(),
        status: response.status(),
        method: response.request().method()
      });
      console.log(`📥 ${response.request().method()} ${response.url()} → ${response.status()}`);

      if (response.status() >= 400) {
        try {
          const body = await response.text();
          console.log(`   ❌ Error body: ${body}`);
        } catch (e) {
          console.log(`   ❌ Could not read error body`);
        }
      }
    }
  });

  // Login
  await login(page);
  console.log('✅ Logged in successfully');

  // Navigate to Overview page
  await page.goto(`${BASE_URL}/dashboard`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  console.log('✅ Overview page loaded');

  // Check for API calls to projects and deliverables
  const projectsCalls = apiCalls.filter(c => c.url.includes('/api/projects'));
  const deliverablesCalls = apiCalls.filter(c => c.url.includes('/api/deliverables'));

  console.log(`\n📊 API Call Summary:`);
  console.log(`   Projects calls: ${projectsCalls.length}`);
  projectsCalls.forEach(c => console.log(`     - ${c.method} ${c.url} → ${c.status}`));

  console.log(`   Deliverables calls: ${deliverablesCalls.length}`);
  deliverablesCalls.forEach(c => console.log(`     - ${c.method} ${c.url} → ${c.status}`));

  // Check for 403 errors
  const forbiddenCalls = apiCalls.filter(c => c.status === 403);
  if (forbiddenCalls.length > 0) {
    console.log(`\n❌ Found ${forbiddenCalls.length} 403 Forbidden responses:`);
    forbiddenCalls.forEach(c => console.log(`   - ${c.method} ${c.url}`));
  } else {
    console.log(`\n✅ No 403 Forbidden errors detected`);
  }

  // Take screenshot of Overview page
  await page.screenshot({ path: 'tests/debug/overview-page.png', fullPage: true });
  console.log('📸 Screenshot saved to tests/debug/overview-page.png');
});
