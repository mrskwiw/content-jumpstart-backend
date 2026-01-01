import { Page } from '@playwright/test';

/**
 * Helper function to login as operator
 */
export async function loginAsOperator(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill('mrskwiw@gmail.com');
  // Use more specific selector to avoid matching "Show password" button
  await page.locator('input[type="password"]').fill('Random!1Pass');
  await page.getByRole('button', { name: /sign in/i }).click();

  // Wait for redirect to dashboard (app redirects to /dashboard not /)
  await page.waitForURL('/dashboard');
}

/**
 * Helper function to create a test project through the wizard
 */
export async function createTestProject(page: Page, projectName: string) {
  await page.goto('/wizard');

  // Step 1: Fill client profile
  await page.getByLabel('Company Name').fill(projectName);
  await page.getByLabel('Business Description').fill('Test company description for automated testing');
  await page.getByLabel('Ideal Customer').fill('Test customers and stakeholders');
  await page.getByLabel('Main Problem Solved').fill('Test problem that needs solving');
  await page.getByRole('button', { name: /continue/i }).click();

  // Step 2: Select templates (increase quantity for template 1)
  const template1 = page.locator('[data-template-id="1"]').first();
  await template1.getByRole('button', { name: /increase/i }).click();
  await page.getByRole('button', { name: /continue/i }).click();

  // Step 3: Skip research
  await page.getByRole('button', { name: /skip/i }).click();

  return page;
}

/**
 * Helper function to wait for content generation to complete
 */
export async function waitForGeneration(page: Page, timeout = 120000) {
  await page.waitForSelector('[data-testid="generation-complete"]', { timeout });
}

/**
 * Helper function to fill wizard step 1 (client profile)
 * NOTE: Form labels don't have htmlFor attributes, so we use placeholder text instead
 * IMPORTANT: This function fills the form but does NOT save it. Call page.getByRole('button', { name: /save profile/i }).click() to save.
 */
export async function fillClientProfile(page: Page, data: {
  companyName: string;
  businessDescription: string;
  idealCustomer: string;
  mainProblemSolved: string;
  painPoints?: string[];
}) {
  // Use placeholder selectors since labels don't have htmlFor attributes
  await page.getByPlaceholder('Acme Corp').fill(data.companyName);

  await page.getByPlaceholder(/cloud-based project management/i).fill(data.businessDescription);

  // Note: "Ideal Customer" field is labeled "Target Audience" in the actual form
  await page.getByPlaceholder(/Small business owners/i).fill(data.idealCustomer);

  await page.getByPlaceholder(/eliminate the chaos/i).fill(data.mainProblemSolved);

  // Pain points section doesn't exist in current wizard implementation
  // Skipping pain points for now
  // TODO: Add pain points functionality to wizard if needed

  // Note: After filling the form, tests must click the "Save Profile" button to trigger save
  // The wizard will automatically advance to the next step after successful save
}

/**
 * Helper function to skip the research step in the wizard
 */
export async function skipResearchStep(page: Page) {
  // Click skip/continue button on research page
  await page.getByRole('button', { name: /skip|continue/i }).click();

  // Wait for templates step to load - verify by looking for the template grid heading
  await page.getByRole('heading', { name: 'Custom Template Quantities' }).waitFor({ timeout: 5000 });
}

/**
 * Helper function to select templates in wizard step 3 (after research)
 * NOTE: Templates don't have data-template-id attributes. We select by template number text.
 */
export async function selectTemplates(page: Page, quantities: Record<number, number>) {
  // Wait for template grid to be fully rendered
  const templateCards = page.locator('.group.relative.rounded-lg.border-2.p-4');
  await templateCards.first().waitFor({ state: 'visible', timeout: 10000 });

  // Verify all template cards are loaded (should be 15 total)
  const cardCount = await templateCards.count();
  console.log(`Found ${cardCount} template cards`);

  for (const [templateId, quantity] of Object.entries(quantities)) {
    // Find all increase buttons (there are 15 templates, each with decrease/increase buttons)
    // Template cards are in a grid, template ID corresponds to position
    // Since templates are ordered 1-15, we can use nth() to find the right one
    const templateIndex = parseInt(templateId) - 1; // Convert to 0-based index

    // Find the template card by index in the grid
    const targetCard = templateCards.nth(templateIndex);

    // Ensure the specific card is visible before clicking
    await targetCard.waitFor({ state: 'visible', timeout: 5000 });

    // Find the increase button within this specific card
    const increaseButton = targetCard.getByRole('button', { name: 'Increase quantity' });

    // Ensure button is visible and enabled
    await increaseButton.waitFor({ state: 'visible', timeout: 5000 });

    // Click the increase button the specified number of times
    for (let i = 0; i < quantity; i++) {
      await increaseButton.click();
      // Small delay to allow UI to update
      await page.waitForTimeout(150);
    }
  }
}
