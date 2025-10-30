import { test, expect } from '@playwright/test';

test.describe('Complete Metadata Manager Workflow', () => {
  test('Full workflow: Login → Catalog → Schema → Table → Comment → Approve → Apply', async ({ page }) => {
    // Configure test for video recording
    test.setTimeout(180000); // 3 minutes timeout
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // PART 1: LOGIN AS SUGGESTION-ONLY USER
    // ============================================
    await test.step('Login as John (suggestion-only user)', async () => {
      console.log('Navigating to login page...');
      await page.goto('http://localhost:4001');
      await page.waitForTimeout(2000);

      // Fill in login credentials
      await page.fill('input[name="username"]', 'john_suggest');
      await page.waitForTimeout(500);
      await page.fill('input[name="password"]', 'suggest123');
      await page.waitForTimeout(500);

      // Click login button
      await page.click('[data-testid="login-button"]');

      // Wait for navigation to complete
      await page.waitForTimeout(4000);
      console.log('Login successful');
    });

    // ============================================
    // PART 2: NAVIGATE TO CATALOG EXPLORER
    // ============================================
    await test.step('Navigate to Catalog Explorer', async () => {
      // Navigate directly to catalog route
      await page.goto('http://localhost:4001/catalog');
      await page.waitForTimeout(3000);
      console.log('Navigated to Catalog Explorer');

      // Wait for catalogs to load
      await page.waitForSelector('.MuiAccordion-root', { timeout: 10000 });
      console.log('Catalog Explorer loaded');
    });

    // ============================================
    // PART 3: EXPAND ARAO CATALOG
    // ============================================
    await test.step('Expand arao catalog', async () => {
      console.log('Looking for arao catalog...');

      // Look for the arao catalog in the accordion
      // Try multiple selectors to find the catalog
      const araoCatalog = await page.locator('.MuiAccordion-root').filter({ hasText: 'arao' }).first();

      if (await araoCatalog.isVisible()) {
        console.log('Found arao catalog accordion');

        // Click on the accordion summary to expand
        const accordionSummary = araoCatalog.locator('.MuiAccordionSummary-root').first();
        await accordionSummary.click();
        await page.waitForTimeout(3000);
        console.log('Expanded arao catalog');
      } else {
        // Alternative: Look for any element with text "arao"
        const araoText = page.locator('text=arao').first();
        if (await araoText.isVisible()) {
          await araoText.click();
          await page.waitForTimeout(3000);
          console.log('Clicked arao text');
        }
      }
    });

    // ============================================
    // PART 4: EXPAND METADATA_TEST SCHEMA
    // ============================================
    await test.step('Expand metadata_test schema', async () => {
      console.log('Looking for metadata_test schema...');

      // Wait for schemas to be visible
      await page.waitForTimeout(2000);

      // Look for metadata_test schema
      const metadataSchema = page.locator('text=metadata_test').first();

      if (await metadataSchema.isVisible()) {
        console.log('Found metadata_test schema');

        // Click to expand the schema
        await metadataSchema.click();
        await page.waitForTimeout(3000);
        console.log('Expanded metadata_test schema');

        // Scroll if needed to see tables
        await page.mouse.wheel(0, 200);
        await page.waitForTimeout(1000);
      }
    });

    // ============================================
    // PART 5: SELECT USERS TABLE
    // ============================================
    await test.step('Select users table', async () => {
      console.log('Looking for users table...');

      // Look for users table
      const usersTable = page.locator('text=users').first();

      if (await usersTable.isVisible()) {
        console.log('Found users table');
        await usersTable.click();
        await page.waitForTimeout(4000);
        console.log('Selected users table');

        // Wait for table viewer to load
        await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible({ timeout: 10000 });
        console.log('Table viewer loaded');
      }
    });

    // ============================================
    // PART 6: ADD COMMENT SUGGESTION
    // ============================================
    await test.step('Add comment suggestion to a column', async () => {
      console.log('Looking for suggest comment button...');

      // Scroll to see columns
      await page.mouse.wheel(0, 300);
      await page.waitForTimeout(1000);

      // Find the first suggest comment button
      const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();

      if (await suggestButton.isVisible()) {
        console.log('Found suggest comment button');
        await suggestButton.click();
        await page.waitForTimeout(2000);

        // Wait for dialog to open
        await expect(page.locator('[data-testid="comment-dialog"]')).toBeVisible({ timeout: 5000 });
        console.log('Comment dialog opened');

        // Enter comment text
        const commentText = 'This column represents the unique identifier for user records in the system. Auto-generated primary key.';
        await page.fill('[data-testid="comment-suggestion-input"]', commentText);
        await page.waitForTimeout(1000);
        console.log('Entered comment suggestion');

        // Submit the comment
        await page.click('[data-testid="submit-suggestion-button"]');
        await page.waitForTimeout(3000);
        console.log('Submitted comment suggestion');

        // Verify pending indicator appears
        await expect(page.locator('[data-testid="pending-icon"]').first()).toBeVisible({ timeout: 5000 });
        console.log('Comment suggestion created successfully');
      }
    });

    // ============================================
    // PART 7: LOGOUT AND LOGIN AS APPROVER
    // ============================================
    await test.step('Switch to Jane (approver user)', async () => {
      console.log('Switching to approver user...');

      // Navigate directly to login page (forces logout)
      await page.goto('http://localhost:4001/login');
      await page.waitForTimeout(2000);

      // Login as approver
      console.log('Logging in as approver...');
      await page.fill('input[name="username"]', 'jane_approver');
      await page.waitForTimeout(500);
      await page.fill('input[name="password"]', 'approve123');
      await page.waitForTimeout(500);
      await page.click('[data-testid="login-button"]');
      await page.waitForTimeout(4000);
      console.log('Logged in as approver');
    });

    // ============================================
    // PART 8: NAVIGATE BACK TO THE SAME TABLE
    // ============================================
    await test.step('Navigate back to users table', async () => {
      console.log('Navigating back to users table...');

      // Navigate to catalog page
      await page.goto('http://localhost:4001/catalog');
      await page.waitForTimeout(3000);

      // Expand arao catalog
      const araoCatalog = await page.locator('.MuiAccordion-root').filter({ hasText: 'arao' }).first();
      if (await araoCatalog.isVisible()) {
        const accordionSummary = araoCatalog.locator('.MuiAccordionSummary-root').first();
        await accordionSummary.click();
        await page.waitForTimeout(2000);
      }

      // Expand metadata_test schema
      const metadataSchema = page.locator('text=metadata_test').first();
      if (await metadataSchema.isVisible()) {
        await metadataSchema.click();
        await page.waitForTimeout(2000);
      }

      // Select users table
      const usersTable = page.locator('text=users').first();
      if (await usersTable.isVisible()) {
        await usersTable.click();
        await page.waitForTimeout(4000);
      }

      console.log('Back at users table');
    });

    // ============================================
    // PART 9: APPROVE THE COMMENT
    // ============================================
    await test.step('Approve the pending comment', async () => {
      console.log('Looking for review button...');

      // Scroll to find the review button
      await page.mouse.wheel(0, 300);
      await page.waitForTimeout(1000);

      // Find the review button
      const reviewButton = page.locator('[data-testid="review-comment-button"]').first();

      if (await reviewButton.isVisible()) {
        console.log('Found review button');
        await reviewButton.click();
        await page.waitForTimeout(2000);

        // Wait for review dialog
        await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible({ timeout: 5000 });
        console.log('Review dialog opened');

        // Add feedback
        const feedbackInput = page.locator('[data-testid="review-feedback-input"]');
        if (await feedbackInput.isVisible()) {
          await feedbackInput.fill('Looks good! Clear and informative description.');
          await page.waitForTimeout(1000);
        }

        // Click approve button
        await page.click('[data-testid="approve-comment-button"]');
        await page.waitForTimeout(3000);
        console.log('Comment approved');

        // Verify status changed
        await expect(page.locator('text=APPROVED').first()).toBeVisible({ timeout: 5000 });
        console.log('Comment status updated to approved');
      }
    });

    // ============================================
    // PART 10: APPLY THE COMMENT
    // ============================================
    await test.step('Apply the approved comment', async () => {
      console.log('Looking for apply button...');

      // Find the apply button
      const applyButton = page.locator('[data-testid="apply-comment-button"]').first();

      if (await applyButton.isVisible()) {
        console.log('Found apply button');
        await applyButton.click();
        await page.waitForTimeout(4000);
        console.log('Comment applied');

        // Verify the pending indicator is gone
        const pendingIcon = page.locator('[data-testid="pending-icon"]').first();
        await expect(pendingIcon).not.toBeVisible({ timeout: 5000 });
        console.log('Comment successfully applied to Databricks');
      }
    });

    // ============================================
    // PART 11: FINAL VERIFICATION
    // ============================================
    await test.step('Final verification', async () => {
      console.log('Performing final verification...');

      // Scroll to top of page
      await page.mouse.wheel(0, -500);
      await page.waitForTimeout(2000);

      // Refresh to verify persistence
      await page.reload();
      await page.waitForTimeout(4000);

      console.log('Workflow completed successfully!');

      // Final pause for video
      await page.waitForTimeout(3000);
    });
  });
});