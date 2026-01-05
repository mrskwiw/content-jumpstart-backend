import { test, expect } from '@playwright/test';

/**
 * Project Wizard E2E Tests
 *
 * Tests the critical 5-step wizard flow:
 * 1. Client selection/creation
 * 2. Brief upload/entry
 * 3. Template selection
 * 4. Generation
 * 5. Review & export
 */

test.describe('Project Wizard', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'mrskwiw@gmail.com');
    await page.fill('input[name="password"]', 'Random!1Pass');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should complete full wizard flow with new client', async ({ page }) => {
    // Click "New Project" button
    await page.click('text=New Project');

    // STEP 1: Client Selection
    await expect(page.locator('text=Select Client')).toBeVisible();

    // Create new client
    await page.click('text=Create New Client');
    await page.fill('input[name="clientName"]', 'Test Company Inc');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="contactPerson"]', 'John Doe');
    await page.click('button:has-text("Create Client")');

    // Wait for client to be created
    await expect(page.locator('text=Test Company Inc')).toBeVisible({ timeout: 10000 });

    // Select the newly created client
    await page.click('text=Test Company Inc');
    await page.click('button:has-text("Next")');

    // STEP 2: Brief Entry
    await expect(page.locator('text=Client Brief')).toBeVisible();

    // Option 1: Upload brief file
    // const fileInput = page.locator('input[type="file"]');
    // await fileInput.setInputFiles('path/to/sample_brief.txt');

    // Option 2: Paste brief text
    await page.click('text=Paste Text');
    const briefText = `
Company Name: Test Company Inc
Business Description: We provide AI-powered content solutions
Ideal Customer: B2B SaaS companies looking to scale content
Main Problem Solved: Time-consuming content creation process
    `;
    await page.fill('textarea[name="briefContent"]', briefText);
    await page.click('button:has-text("Next")');

    // STEP 3: Template Selection
    await expect(page.locator('text=Template Selection')).toBeVisible();

    // Select template quantities
    await page.fill('input[name="template_1"]', '3');
    await page.fill('input[name="template_2"]', '5');
    await page.fill('input[name="template_9"]', '2');

    await page.click('button:has-text("Next")');

    // STEP 4: Generation
    await expect(page.locator('text=Generate Content')).toBeVisible();

    // Verify summary shows correct counts
    await expect(page.locator('text=10 posts')).toBeVisible(); // 3+5+2

    // Start generation
    await page.click('button:has-text("Start Generation")');

    // Wait for generation to complete (can take up to 60 seconds)
    await expect(page.locator('text=Generation Complete')).toBeVisible({ timeout: 120000 });

    // STEP 5: Review & Export
    await expect(page.locator('text=Review Content')).toBeVisible();

    // Verify posts are displayed
    await expect(page.locator('[data-testid="post-card"]')).toHaveCount(10);

    // Export deliverable
    await page.click('button:has-text("Export")');
    await page.click('text=Download DOCX');

    // Wait for download
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Download")');
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/Test_Company_Inc.*\.docx/);
  });

  test('should handle validation errors gracefully', async ({ page }) => {
    await page.click('text=New Project');

    // Try to proceed without selecting client
    await page.click('button:has-text("Next")');

    // Should show validation error
    await expect(page.locator('text=Please select a client')).toBeVisible();

    // Should not advance to next step
    await expect(page.locator('text=Select Client')).toBeVisible();
  });

  test('should allow going back to previous steps', async ({ page }) => {
    await page.click('text=New Project');

    // Create and select client
    await page.click('text=Create New Client');
    await page.fill('input[name="clientName"]', 'Test Client 2');
    await page.fill('input[name="email"]', 'test2@example.com');
    await page.click('button:has-text("Create Client")');
    await page.click('text=Test Client 2');
    await page.click('button:has-text("Next")');

    // Go to brief step
    await expect(page.locator('text=Client Brief')).toBeVisible();

    // Click "Back" button
    await page.click('button:has-text("Back")');

    // Should return to client selection
    await expect(page.locator('text=Select Client')).toBeVisible();

    // Should still have selected client
    await expect(page.locator('text=Test Client 2').locator('input[type="radio"]')).toBeChecked();
  });

  test('should save progress and allow resuming later', async ({ page }) => {
    await page.click('text=New Project');

    // Start wizard flow
    await page.click('text=Create New Client');
    await page.fill('input[name="clientName"]', 'Resume Test Client');
    await page.fill('input[name="email"]', 'resume@example.com');
    await page.click('button:has-text("Create Client")');
    await page.click('text=Resume Test Client');
    await page.click('button:has-text("Next")');

    // Enter brief
    await page.fill('textarea[name="briefContent"]', 'Test brief content');
    await page.click('button:has-text("Save Draft")');

    // Navigate away
    await page.goto('/dashboard');

    // Return to wizard
    await page.click('text=Resume Test Client');

    // Should resume at last saved step (Brief)
    await expect(page.locator('text=Client Brief')).toBeVisible();
    await expect(page.locator('textarea[name="briefContent"]')).toHaveValue('Test brief content');
  });
});
