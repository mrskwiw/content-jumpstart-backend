import { test, expect } from '@playwright/test';

/**
 * Authentication E2E Tests
 *
 * Critical workflows:
 * 1. Login with valid credentials
 * 2. Login with invalid credentials (error handling)
 * 3. Protected route redirect (unauthenticated)
 * 4. Logout functionality
 */

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage and cookies before each test
    await page.context().clearCookies();
    await page.goto('/');
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');

    // Fill in credentials
    await page.fill('input[name="email"]', 'mrskwiw@gmail.com');
    await page.fill('input[name="password"]', 'Random!1Pass');

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for navigation to dashboard
    await page.waitForURL('/dashboard', { timeout: 5000 });

    // Verify dashboard elements are visible
    await expect(page.locator('text=Dashboard')).toBeVisible();
    await expect(page.locator('text=Projects')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');

    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible({ timeout: 5000 });

    // Should still be on login page
    await expect(page).toHaveURL(/.*login/);
  });

  test('should redirect to login when accessing protected route', async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto('/dashboard');

    // Should redirect to login
    await page.waitForURL(/.*login/, { timeout: 5000 });

    await expect(page.locator('text=Sign in')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="email"]', 'mrskwiw@gmail.com');
    await page.fill('input[name="password"]', 'Random!1Pass');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');

    // Click logout button
    await page.click('[aria-label="User menu"]');
    await page.click('text=Logout');

    // Should redirect to login
    await page.waitForURL(/.*login/, { timeout: 5000 });

    // Verify cannot access dashboard anymore
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*login/);
  });
});
