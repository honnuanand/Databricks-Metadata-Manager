import { test, expect } from '@playwright/test';

test.describe('Debug Catalog Workflow', () => {
  test('Debug: Check catalog loading and interaction', async ({ page }) => {
    // Configure test
    test.setTimeout(120000);
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Step 1: Login
    console.log('Step 1: Logging in...');
    await page.goto('http://localhost:4001');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/debug-1-login-page.png' });

    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'test-results/debug-2-after-login.png' });
    console.log('Login complete, URL:', page.url());

    // Step 2: Navigate to catalog
    console.log('Step 2: Navigating to catalog...');
    await page.goto('http://localhost:4001/catalog');
    await page.waitForTimeout(5000); // Give more time for data to load
    await page.screenshot({ path: 'test-results/debug-3-catalog-page.png' });
    console.log('On catalog page, URL:', page.url());

    // Step 3: Check what's on the page
    console.log('Step 3: Checking page content...');

    // Check if there's any error message
    const errorElements = await page.locator('.MuiAlert-root').count();
    if (errorElements > 0) {
      console.log('Found error alert on page');
      const errorText = await page.locator('.MuiAlert-root').first().textContent();
      console.log('Error message:', errorText);
    }

    // Check if loading spinner is present
    const loadingSpinner = await page.locator('.MuiCircularProgress-root').count();
    console.log('Loading spinners found:', loadingSpinner);

    // Check for accordions
    const accordions = await page.locator('.MuiAccordion-root').count();
    console.log('Accordions found:', accordions);

    // Check for any text containing "arao"
    const araoElements = await page.locator('text=arao').count();
    console.log('Elements with "arao" text:', araoElements);

    // Check for any paper/card elements
    const papers = await page.locator('.MuiPaper-root').count();
    console.log('Paper elements found:', papers);

    // Get all visible text on the page
    const bodyText = await page.locator('body').innerText();
    console.log('Page contains text length:', bodyText.length);

    // If page seems empty, try to find catalog elements with different selectors
    if (accordions === 0) {
      console.log('No accordions found, trying alternative selectors...');

      // Try to find any catalog-related elements
      const catalogElements = await page.locator('[class*="catalog" i]').count();
      console.log('Elements with catalog in class:', catalogElements);

      // Check if we're getting a different page or component
      const h4Elements = await page.locator('h4').count();
      console.log('H4 headers found:', h4Elements);
      if (h4Elements > 0) {
        const h4Text = await page.locator('h4').first().textContent();
        console.log('First H4 text:', h4Text);
      }
    }

    // Step 4: Try clicking on arao if it exists
    if (araoElements > 0) {
      console.log('Step 4: Trying to click on arao...');
      await page.locator('text=arao').first().click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'test-results/debug-4-after-arao-click.png' });

      // Check for schemas
      const metadataElements = await page.locator('text=metadata_test').count();
      console.log('Elements with "metadata_test" text:', metadataElements);

      if (metadataElements > 0) {
        console.log('Step 5: Clicking on metadata_test...');
        await page.locator('text=metadata_test').first().click();
        await page.waitForTimeout(3000);
        await page.screenshot({ path: 'test-results/debug-5-after-schema-click.png' });

        // Check for tables
        const usersElements = await page.locator('text=users').count();
        console.log('Elements with "users" text:', usersElements);
      }
    } else {
      console.log('No arao catalog found on page!');
      // Log the actual page content for debugging
      const pageTitle = await page.title();
      console.log('Page title:', pageTitle);

      // Check if we're still authenticated
      const userMenuElements = await page.locator('[data-testid*="user"]').count();
      console.log('User menu elements:', userMenuElements);
    }

    // Final screenshot
    await page.screenshot({ path: 'test-results/debug-final.png', fullPage: true });
    console.log('Debug test complete');
  });
});