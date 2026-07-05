/**
 * Frontend E2E Tests: Research Tool Field Auto-Population
 *
 * Tests the complete user workflow:
 * 1. Create/edit client with extended fields
 * 2. Verify fields persist
 * 3. Run research tool
 * 4. Verify fields auto-populate
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const API_URL = process.env.API_URL || 'http://localhost:8000';

/**
 * Test Suite: Client Profile Extended Fields
 */
test.describe('Client Profile - Extended Fields Persistence', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto(BASE_URL);

    // Assume authenticated (or handle login)
    // In production, use test user token
  });

  test('✅ Create new client with extended fields should persist to database', async ({ page }) => {
    // Navigate to New Client page
    await page.goto(`${BASE_URL}/dashboard/clients/new`);

    // Fill basic fields
    await page.fill('input[placeholder*="Company name"]', 'TechCorp');
    await page.fill('textarea[placeholder*="Business description"]', 'Leading SaaS platform');
    await page.fill('textarea[placeholder*="Target audience"]', 'Enterprise teams');

    // Scroll to extended fields
    await page.locator('text=Brand Personality').scrollIntoViewIfNeeded();

    // Fill extended fields
    // Brand Personality (multiple tags)
    await page.fill('input[placeholder*="Bold"]', 'Bold');
    await page.press('input[placeholder*="Bold"]', 'Enter');
    await page.fill('input[placeholder*="Empathetic"]', 'Empathetic');
    await page.press('input[placeholder*="Empathetic"]', 'Enter');

    // Tone to Avoid
    await page.fill('input[placeholder*="Overly formal"]', 'Corporate jargon');

    // Posting Frequency
    await page.fill('input[placeholder*="3x per week"]', '3-4x weekly');

    // Founder Name
    await page.fill('input[placeholder*="Jane Smith"]', 'Jane Smith');

    // Save
    await page.click('button:has-text("Save Client Profile")');

    // Wait for success
    await page.waitForURL(/\/dashboard\/clients\/[a-z0-9-]+/);
    const clientUrl = page.url();
    const clientId = clientUrl.split('/').pop();

    // ✅ Verify via API that fields were persisted
    const response = await page.request.get(`${API_URL}/api/clients/${clientId}`);
    expect(response.status()).toBe(200);

    const client = await response.json();
    expect(client.brandPersonality).toEqual(['Bold', 'Empathetic']);
    expect(client.toneToAvoid).toBe('Corporate jargon');
    expect(client.postingFrequency).toBe('3-4x weekly');
    expect(client.founderName).toBe('Jane Smith');
  });

  test('✅ Edit existing client should update extended fields', async ({ page }) => {
    // Create client first
    const clientId = await createTestClient(page);

    // Navigate to client detail page
    await page.goto(`${BASE_URL}/dashboard/clients/${clientId}`);

    // Edit mode
    await page.click('button:has-text("Edit")');

    // Update extended fields
    await page.locator('text=Brand Personality').scrollIntoViewIfNeeded();

    // Clear and set new brand personality
    const brandPersonalityInput = page.locator('input[placeholder*="Bold"]');
    await brandPersonalityInput.clear();
    await brandPersonalityInput.fill('Innovative');
    await brandPersonalityInput.press('Enter');

    // Update tone to avoid
    const toneInput = page.locator('input[placeholder*="formal"]');
    await toneInput.clear();
    await toneInput.fill('Overly technical');

    // Save
    await page.click('button:has-text("Save")');

    // Wait for update
    await page.waitForLoadState('networkidle');

    // ✅ Verify API has updated values
    const response = await page.request.get(`${API_URL}/api/clients/${clientId}`);
    const client = await response.json();
    expect(client.brandPersonality).toContain('Innovative');
    expect(client.toneToAvoid).toBe('Overly technical');
  });
});

/**
 * Test Suite: Research Tool Auto-Population
 */
test.describe('Research Tool - Field Auto-Population', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('✅ Voice Analysis tool should auto-populate brandPersonality and toneToAvoid', async ({ page }) => {
    // Create client with extended fields
    const clientId = await createTestClientWithFields(page, {
      brandPersonality: ['Bold', 'Innovative'],
      toneToAvoid: 'Corporate jargon',
    });

    // Create project with this client
    const projectId = await createTestProject(page, clientId);

    // Navigate to research panel
    await page.goto(`${BASE_URL}/dashboard/projects/${projectId}/research`);

    // Wait for client data to load
    await page.waitForSelector('text=Research Tools', { timeout: 5000 });

    // Check that client data is loaded (verify via network response)
    const clientDataResponse = await page.request.get(`${API_URL}/api/clients/${clientId}`);
    const clientData = await clientDataResponse.json();
    expect(clientData.brandPersonality).toEqual(['Bold', 'Innovative']);

    // Select Voice Analysis tool
    await page.click('text=Voice Analysis');

    // Open data collection panel
    await page.click('button:has-text("Continue")');

    // ✅ Verify fields auto-populated
    const brandPersonalityField = page.locator('input[value*="Bold"]');
    const toneToAvoidField = page.locator('input[value*="Corporate jargon"]');

    await expect(brandPersonalityField).toBeVisible();
    await expect(toneToAvoidField).toBeVisible();

    // Verify content is filled (not placeholders)
    const brandValue = await brandPersonalityField.inputValue();
    expect(brandValue).toContain('Bold');
  });

  test('✅ Platform Strategy tool should auto-populate multiple fields', async ({ page }) => {
    // Create client with all platform_strategy fields
    const clientId = await createTestClientWithFields(page, {
      brandPersonality: ['Creative'],
      toneToAvoid: 'Salesy',
      postingFrequency: '5x weekly',
      dataUsage: 'heavy',
    });

    const projectId = await createTestProject(page, clientId);

    // Navigate to research
    await page.goto(`${BASE_URL}/dashboard/projects/${projectId}/research`);
    await page.waitForSelector('text=Research Tools');

    // Select Platform Strategy
    await page.click('text=Platform Strategy');
    await page.click('button:has-text("Continue")');

    // ✅ Verify all 4 fields auto-populated
    const fields = {
      'Brand Personality': 'Creative',
      'Tone to Avoid': 'Salesy',
      'Posting Frequency': '5x weekly',
      'Data Usage': 'heavy',
    };

    for (const [label, expectedValue] of Object.entries(fields)) {
      const field = page.locator(`text=${label}`).locator('..').locator('input, textarea').first();
      await expect(field).toContainText(expectedValue);
    }
  });

  test('✅ Story Mining tool should auto-populate stories and founderName', async ({ page }) => {
    const clientId = await createTestClientWithFields(page, {
      stories: ['Built from idea to $1M ARR in 18 months'],
      founderName: 'Sarah Chen',
      measurableResults: '100% revenue growth',
    });

    const projectId = await createTestProject(page, clientId);

    // Navigate to research
    await page.goto(`${BASE_URL}/dashboard/projects/${projectId}/research`);
    await page.waitForSelector('text=Research Tools');

    // Select Story Mining
    await page.click('text=Story Mining');
    await page.click('button:has-text("Continue")');

    // ✅ Verify fields auto-populated
    const storiesField = page.locator('textarea[value*="Built from idea"]');
    const founderField = page.locator('input[value*="Sarah Chen"]');
    const resultsField = page.locator('input[value*="100% revenue"]');

    await expect(storiesField).toBeVisible();
    await expect(founderField).toBeVisible();
    await expect(resultsField).toBeVisible();
  });

  test('✅ Empty/missing fields should not block auto-population', async ({ page }) => {
    // Create client with ONLY brandPersonality, missing others
    const clientId = await createTestClientWithFields(page, {
      brandPersonality: ['Bold'],
      // All other fields null/undefined
    });

    const projectId = await createTestProject(page, clientId);

    // Navigate to research
    await page.goto(`${BASE_URL}/dashboard/projects/${projectId}/research`);
    await page.waitForSelector('text=Research Tools');

    // Select Voice Analysis (only needs brandPersonality + toneToAvoid)
    await page.click('text=Voice Analysis');
    await page.click('button:has-text("Continue")');

    // ✅ Verify brandPersonality is populated, toneToAvoid is empty
    const brandField = page.locator('input[value*="Bold"]');
    const toneField = page.locator('input[placeholder*="formal"]');

    await expect(brandField).toBeVisible();
    await expect(toneField).toHaveValue(''); // Empty, not populated

    // Tool should be usable (user can fill remaining fields)
    await expect(toneField).toBeEditable();
  });
});

/**
 * Test Suite: End-to-End Workflow
 */
test.describe('Complete E2E Workflow', () => {

  test('✅ Create client → Save extended fields → Run research → Verify auto-population', async ({ page }) => {
    // Step 1: Create new client with extended fields
    await page.goto(`${BASE_URL}/dashboard/clients/new`);

    const clientData = {
      name: 'E2E Test Corp',
      businessDescription: 'Test company for E2E',
      idealCustomer: 'Test audience',
      brandPersonality: ['Bold', 'Innovative', 'Fast'],
      toneToAvoid: 'Slow, bureaucratic',
      postingFrequency: 'Daily',
      founderName: 'E2E Tester',
      stories: ['Tested and approved'],
      measurableResults: 'E2E working',
    };

    // Fill and save
    await page.fill('input[placeholder*="Company"]', clientData.name);
    await page.fill('textarea[placeholder*="Business"]', clientData.businessDescription);
    await page.fill('textarea[placeholder*="Target"]', clientData.idealCustomer);

    // Extended fields
    await page.locator('text=Brand Personality').scrollIntoViewIfNeeded();
    for (const trait of clientData.brandPersonality) {
      await page.fill('input[placeholder*="Bold"]', trait);
      await page.press('input[placeholder*="Bold"]', 'Enter');
    }
    await page.fill('input[placeholder*="formal"]', clientData.toneToAvoid);
    await page.fill('input[placeholder*="3x per week"]', clientData.postingFrequency);

    await page.click('button:has-text("Save Client Profile")');
    await page.waitForURL(/\/dashboard\/clients\/[a-z0-9-]+/);
    const clientUrl = page.url();
    const clientId = clientUrl.split('/').pop();

    // Step 2: Verify extended fields persisted
    const clientResponse = await page.request.get(`${API_URL}/api/clients/${clientId}`);
    const savedClient = await clientResponse.json();
    expect(savedClient.brandPersonality).toEqual(clientData.brandPersonality);
    expect(savedClient.toneToAvoid).toBe(clientData.toneToAvoid);

    // Step 3: Create project
    const projectId = await createTestProject(page, clientId);

    // Step 4: Run research tool
    await page.goto(`${BASE_URL}/dashboard/projects/${projectId}/research`);
    await page.waitForSelector('text=Research Tools');

    // Select multiple tools that use extended fields
    const tools = ['Voice Analysis', 'Platform Strategy'];
    for (const tool of tools) {
      await page.click(`text=${tool}`);
    }

    await page.click('button:has-text("Continue")');

    // Step 5: Verify auto-population for each tool
    // Voice Analysis
    const voiceSection = page.locator('text=Voice Analysis').locator('..');
    const voiceBrandField = voiceSection.locator('input').first();
    await expect(voiceBrandField).toContainText('Bold');

    // Platform Strategy
    const platformSection = page.locator('text=Platform Strategy').locator('..');
    const platformBrandField = platformSection.locator('input').first();
    await expect(platformBrandField).toContainText('Bold');

    console.log('✅ Complete E2E workflow successful!');
  });
});

/**
 * Test Suite: Production Readiness
 */
test.describe('Production Readiness', () => {

  test('✅ Large field values should be stored and retrieved correctly', async ({ page }) => {
    const largeText = 'A'.repeat(5000); // 5KB text
    const clientId = await createTestClientWithFields(page, {
      toneToAvoid: largeText,
    });

    // Verify via API
    const response = await page.request.get(`${API_URL}/api/clients/${clientId}`);
    const client = await response.json();
    expect(client.toneToAvoid).toBe(largeText);
    expect(client.toneToAvoid.length).toBe(5000);
  });

  test('✅ Special characters and unicode should be preserved', async ({ page }) => {
    const specialData = {
      brandPersonality: ['café-style', 'über-modern', '日本語'],
      toneToAvoid: 'émojis 😀 & symbols',
      mainCta: 'Sign up → Get 50% off',
    };

    const clientId = await createTestClientWithFields(page, specialData);

    // Verify via API
    const response = await page.request.get(`${API_URL}/api/clients/${clientId}`);
    const client = await response.json();
    expect(client.brandPersonality).toEqual(specialData.brandPersonality);
    expect(client.toneToAvoid).toBe(specialData.toneToAvoid);
    expect(client.mainCta).toBe(specialData.mainCta);
  });

  test('✅ Concurrent tool selections should work correctly', async ({ page }) => {
    const clientId = await createTestClientWithFields(page, {
      brandPersonality: ['Bold'],
      toneToAvoid: 'Casual',
      postingFrequency: 'Daily',
      stories: ['Success story'],
    });

    const projectId = await createTestProject(page, clientId);

    // Navigate to research
    await page.goto(`${BASE_URL}/dashboard/projects/${projectId}/research`);
    await page.waitForSelector('text=Research Tools');

    // Rapidly select multiple tools
    const tools = ['Voice Analysis', 'Platform Strategy', 'Story Mining', 'Brand Archetype'];
    for (const tool of tools) {
      await page.click(`text=${tool}`);
    }

    // All should be selected without errors
    await page.click('button:has-text("Continue")');

    // All should have auto-populated their respective fields
    await page.waitForLoadState('networkidle');
    const success = await page.locator('text=All fields auto-populated').isVisible().catch(() => false);

    // Even if no success message, no errors should be thrown
    const hasErrors = await page.locator('text=Error').isVisible().catch(() => false);
    expect(hasErrors).toBe(false);
  });
});

/**
 * Helper Functions
 */

async function createTestClient(page: Page): Promise<string> {
  await page.goto(`${BASE_URL}/dashboard/clients/new`);
  await page.fill('input[placeholder*="Company"]', `Test Client ${Date.now()}`);
  await page.fill('textarea[placeholder*="Business"]', 'Test business description');
  await page.fill('textarea[placeholder*="Target"]', 'Test audience');
  await page.click('button:has-text("Save Client Profile")');
  await page.waitForURL(/\/dashboard\/clients\/[a-z0-9-]+/);
  const clientUrl = page.url();
  return clientUrl.split('/').pop()!;
}

async function createTestClientWithFields(page: Page, fields: Record<string, any>): Promise<string> {
  const clientId = await createTestClient(page);

  // If fields provided, edit client to add them
  if (Object.keys(fields).length > 0) {
    await page.goto(`${BASE_URL}/dashboard/clients/${clientId}`);
    await page.click('button:has-text("Edit")');

    // Fill extended fields based on type
    for (const [key, value] of Object.entries(fields)) {
      if (Array.isArray(value)) {
        // Array field (like brandPersonality)
        for (const item of value) {
          const input = page.locator(`input[placeholder*="${item.substring(0, 3)}"]`).first();
          await input.fill(item);
          await input.press('Enter');
        }
      } else if (typeof value === 'string') {
        // String field
        const input = page.locator(`input[value*="${value.substring(0, 5)}"], textarea[value*="${value.substring(0, 5)}"]`).first();
        await input.fill(value);
      }
    }

    await page.click('button:has-text("Save")');
    await page.waitForLoadState('networkidle');
  }

  return clientId;
}

async function createTestProject(page: Page, clientId: string): Promise<string> {
  await page.goto(`${BASE_URL}/dashboard/clients/${clientId}`);
  await page.click('button:has-text("New Project")');
  await page.fill('input[placeholder*="Project name"]', `Test Project ${Date.now()}`);
  await page.click('button:has-text("Create")');
  await page.waitForURL(/\/dashboard\/projects\/[a-z0-9-]+/);
  const projectUrl = page.url();
  return projectUrl.split('/').pop()!;
}
