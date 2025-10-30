import { test, expect } from '@playwright/test';

test.describe('Metadata Manager Workflow Demo', () => {
  test('Demo: Login → Browse Catalog → View Table → Add Comment', async ({ page }) => {
    // Configure test to be slower for better video visibility
    test.setTimeout(120000); // 2 minutes timeout
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // PART 1: LOGIN
    // ============================================
    await test.step('Open application and login', async () => {
      await page.goto('http://localhost:4001');
      await page.waitForTimeout(3000); // Show login page

      // Enter credentials for suggestion-only user
      await page.fill('input[name="username"]', 'john_suggest');
      await page.waitForTimeout(500);
      await page.fill('input[name="password"]', 'suggest123');
      await page.waitForTimeout(500);

      // Click login
      await page.click('[data-testid="login-button"]');
      await page.waitForTimeout(5000); // Wait for login and redirect
    });

    // ============================================
    // PART 2: NAVIGATE TO CATALOG EXPLORER
    // ============================================
    await test.step('Navigate to Catalog Explorer', async () => {
      // Check if we're already on catalog explorer or need to navigate
      const url = page.url();
      if (!url.includes('catalog')) {
        // Click on Catalog Explorer link in navigation
        const catalogLink = page.locator('a:has-text("Catalog Explorer")').first();
        if (await catalogLink.isVisible()) {
          await catalogLink.click();
          await page.waitForTimeout(3000);
        }
      }
    });

    // ============================================
    // PART 3: EXPLORE CATALOG HIERARCHY
    // ============================================
    await test.step('Browse catalog hierarchy', async () => {
      // Wait for catalogs to load
      await page.waitForTimeout(2000);

      // Click on arao catalog - using the accordion or the catalog name
      const araoCatalog = page.locator('div:has-text("arao")').locator('..').first();
      await araoCatalog.click();
      await page.waitForTimeout(3000); // Wait for schemas to load

      // Look for metadata_test schema and click it
      const metadataSchema = page.locator('text=metadata_test').first();
      if (await metadataSchema.isVisible()) {
        await metadataSchema.click();
        await page.waitForTimeout(3000); // Wait for tables to load
      }

      // Click on a table (users or products)
      const usersTable = page.locator('text=/users|products|customers/i').first();
      if (await usersTable.isVisible()) {
        await usersTable.click();
        await page.waitForTimeout(4000); // Wait for table details to load
      }
    });

    // ============================================
    // PART 4: VIEW TABLE DETAILS
    // ============================================
    await test.step('View table schema and columns', async () => {
      // Scroll through the table viewer to show columns
      await page.mouse.wheel(0, 300);
      await page.waitForTimeout(2000);

      // Scroll back up
      await page.mouse.wheel(0, -300);
      await page.waitForTimeout(2000);
    });

    // ============================================
    // PART 5: ADD COMMENT SUGGESTION (if button exists)
    // ============================================
    await test.step('Try to add a comment suggestion', async () => {
      // Look for comment suggestion button
      const suggestButton = page.locator('button').filter({ hasText: /suggest|comment/i }).first();

      if (await suggestButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await suggestButton.click();
        await page.waitForTimeout(2000);

        // If dialog opened, fill in a comment
        const commentInput = page.locator('textarea, input[type="text"]').last();
        if (await commentInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await commentInput.fill('This is a demo comment suggestion for better documentation.');
          await page.waitForTimeout(2000);

          // Try to submit
          const submitButton = page.locator('button').filter({ hasText: /submit|save/i }).first();
          if (await submitButton.isVisible()) {
            await submitButton.click();
            await page.waitForTimeout(3000);
          }
        }
      }
    });

    // ============================================
    // PART 6: LOGOUT AND LOGIN AS ADMIN
    // ============================================
    await test.step('Switch to admin user', async () => {
      // Try to find logout option
      const userMenu = page.locator('[aria-label*="user" i], [data-testid*="user" i]').first();
      if (await userMenu.isVisible({ timeout: 2000 }).catch(() => false)) {
        await userMenu.click();
        await page.waitForTimeout(1000);
      }

      // Look for logout
      const logoutOption = page.locator('text=/logout|sign out/i').first();
      if (await logoutOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await logoutOption.click();
        await page.waitForTimeout(3000);

        // Now login as admin
        await page.fill('input[name="username"]', 'admin_user');
        await page.waitForTimeout(500);
        await page.fill('input[name="password"]', 'admin123');
        await page.waitForTimeout(500);
        await page.click('[data-testid="login-button"]');
        await page.waitForTimeout(5000);

        // Navigate back to the same location
        const catalogLink = page.locator('a:has-text("Catalog Explorer")').first();
        if (await catalogLink.isVisible()) {
          await catalogLink.click();
          await page.waitForTimeout(3000);
        }
      }
    });

    // ============================================
    // PART 7: FINAL STATE
    // ============================================
    await test.step('Show final state', async () => {
      await page.waitForTimeout(3000);
      console.log('Demo workflow completed!');
    });
  });
});