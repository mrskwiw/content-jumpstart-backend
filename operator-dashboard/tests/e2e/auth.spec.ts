import { test, expect } from '@playwright/test';
import { validCredentials, invalidCredentials } from '../fixtures/test-data';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth tokens
    await page.context().clearCookies();
    await page.goto('/login');
  });

  test('should display login page correctly', async ({ page }) => {
    // Verify login page elements
    await expect(page).toHaveTitle(/operator dashboard|login/i);
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    // Fill login form
    await page.getByLabel(/email/i).fill(validCredentials.email);
    await page.locator('input[type="password"]').fill(validCredentials.password);

    // Submit
    await page.getByRole('button', { name: /sign in/i }).click();

    // Verify redirect to dashboard
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });

    // Verify dashboard elements are visible (use specific element to avoid strict mode violation)
    await expect(page.getByRole('link', { name: /projects/i })).toBeVisible({ timeout: 5000 });
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Fill with wrong credentials
    await page.getByLabel(/email/i).fill(invalidCredentials.email);
    await page.locator('input[type="password"]').fill(invalidCredentials.password);
    await page.getByRole('button', { name: /sign in/i }).click();

    // Verify error message appears (backend returns "Incorrect email or password")
    await expect(
      page.getByText(/incorrect email or password/i)
    ).toBeVisible({ timeout: 5000 });

    // Should still be on login page
    await expect(page).toHaveURL(/login/);
  });

  test('should show validation error for empty fields', async ({ page }) => {
    // Try to submit without filling fields
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show validation errors
    // Note: This might be browser-level validation or custom validation
    const emailInput = page.getByLabel(/email/i);
    await expect(emailInput).toBeFocused();
  });

  test('should show validation error for invalid email format', async ({ page }) => {
    // Fill with invalid email format
    await page.getByLabel(/email/i).fill('notanemail');
    await page.locator('input[type="password"]').fill('somepassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show email validation error or prevent submission
    const emailInput = page.getByLabel(/email/i);
    const validationMessage = await emailInput.evaluate(
      (el: HTMLInputElement) => el.validationMessage
    );

    expect(validationMessage).toBeTruthy();
  });

  test('should persist session after page refresh', async ({ page }) => {
    // Login first
    await page.getByLabel(/email/i).fill(validCredentials.email);
    await page.locator('input[type="password"]').fill(validCredentials.password);
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL('/dashboard');

    // Refresh the page
    await page.reload();

    // Should still be logged in (not redirected to login)
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('link', { name: /projects/i })).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.getByLabel(/email/i).fill(validCredentials.email);
    await page.locator('input[type="password"]').fill(validCredentials.password);
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL('/dashboard');

    // Wait for dashboard to fully load before looking for logout button
    await expect(page.getByRole('link', { name: /projects/i })).toBeVisible();

    // Find and click logout button
    const logoutButton = page.getByRole('button', { name: /logout/i });
    await expect(logoutButton).toBeVisible();

    if (await logoutButton.isVisible()) {
      await logoutButton.click();
    } else {
      // Logout might be in a dropdown menu
      const userMenu = page.getByRole('button', { name: /user|account|profile/i });
      if (await userMenu.isVisible()) {
        await userMenu.click();
        await page.getByRole('menuitem', { name: /logout|sign out/i }).click();
      }
    }

    // Verify redirect to login page
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
  });

  test('should prevent access to protected routes when not logged in', async ({ page }) => {
    // Try to access dashboard without logging in
    await page.goto('/dashboard');

    // Should be redirected to login
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
  });

  test('should handle network errors gracefully', async ({ page, context }) => {
    // Fill form first while online
    await page.getByLabel(/email/i).fill(validCredentials.email);
    await page.locator('input[type="password"]').fill(validCredentials.password);

    // Simulate offline mode BEFORE submission
    await context.setOffline(true);

    // Try to submit while offline
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show network error message (actual message from errorMessages.ts)
    await expect(
      page.getByText(/cannot reach the server/i)
    ).toBeVisible({ timeout: 5000 });

    // Re-enable network
    await context.setOffline(false);
  });

  test('should handle slow network gracefully', async ({ page }) => {
    // Slow down network to simulate slow connection
    await page.route('**/api/auth/login', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
      await route.continue();
    });

    await page.getByLabel(/email/i).fill(validCredentials.email);
    await page.locator('input[type="password"]').fill(validCredentials.password);
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show loading state
    const submitButton = page.getByRole('button', { name: /sign in|signing in/i });
    await expect(submitButton).toBeDisabled();

    // Eventually should complete
    await expect(page).toHaveURL('/dashboard', { timeout: 15000 });
  });
});
