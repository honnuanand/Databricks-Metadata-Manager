import { test, expect } from '@playwright/test';

test.describe('Complete Metadata Manager Workflow', () => {
  test('Full workflow: Login → Explore Catalog → Add Comment → Switch User → Approve → Apply', async ({ page }) => {
    // Configure test to be slower for better video visibility
    test.setTimeout(120000); // 2 minutes timeout

    // Start recording with better quality settings
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // PART 1: LOGIN AS SUGGESTION-ONLY USER
    // ============================================
    await test.step('Login as suggestion-only user', async () => {
      await page.goto('http://localhost:4001');
      await page.waitForTimeout(2000); // Allow time for page to load

      // Wait for login button to be visible
      await page.waitForSelector('[data-testid="login-button"]', { timeout: 10000 });

      // Enter credentials
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');

      // Click login button
      await page.click('[data-testid="login-button"]');

      // Wait for navigation to complete
      await page.waitForTimeout(5000); // Give time for login and redirect
    });

    // ============================================
    // PART 2: EXPLORE CATALOG HIERARCHY
    // ============================================
    await test.step('Navigate to Catalog Explorer', async () => {
      // Click on Catalog Explorer if not already there
      const catalogLink = page.getByRole('link', { name: /catalog explorer/i });
      if (await catalogLink.isVisible()) {
        await catalogLink.click();
      }

      await page.waitForTimeout(2000);
    });

    await test.step('Expand arao catalog', async () => {
      // Find and click on the arao catalog accordion
      const araoCatalog = page.locator('text=arao').first();
      await araoCatalog.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // Click to expand the catalog
      await araoCatalog.click();
      await page.waitForTimeout(2000); // Wait for schemas to load

      // Verify schemas are visible
      await expect(page.locator('text=metadata_test')).toBeVisible({ timeout: 10000 });
    });

    await test.step('Expand metadata_test schema', async () => {
      // Find and click on metadata_test schema
      const metadataTestSchema = page.locator('text=metadata_test').first();
      await metadataTestSchema.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // Click to expand the schema
      await metadataTestSchema.click();
      await page.waitForTimeout(2000); // Wait for tables to load

      // Verify tables are visible
      await expect(page.locator('text=users').or(page.locator('text=products'))).toBeVisible({ timeout: 10000 });
    });

    await test.step('Select users table', async () => {
      // Click on the users table
      const usersTable = page.locator('text=users').first();
      await usersTable.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      await usersTable.click();
      await page.waitForTimeout(3000); // Wait for table details to load

      // Verify table viewer is displayed
      await expect(page.getByTestId('table-viewer')).toBeVisible({ timeout: 10000 });
    });

    // ============================================
    // PART 3: ADD COMMENT SUGGESTION
    // ============================================
    await test.step('Add comment suggestion to a column', async () => {
      // Find the first column with a suggest comment button
      const suggestButton = page.getByTestId('suggest-comment-button').first();
      await suggestButton.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // Click suggest comment button
      await suggestButton.click();
      await page.waitForTimeout(2000);

      // Wait for comment dialog
      await expect(page.getByTestId('comment-dialog')).toBeVisible({ timeout: 10000 });

      // Enter comment suggestion
      const commentText = 'This column contains the unique identifier for user records. It is auto-generated and should not be modified manually.';
      await page.fill('[data-testid="comment-suggestion-input"]', commentText);
      await page.waitForTimeout(1000);

      // Submit the suggestion
      await page.click('[data-testid="submit-suggestion-button"]');
      await page.waitForTimeout(2000);

      // Verify the pending comment indicator appears
      await expect(page.getByTestId('pending-icon').first()).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(2000);
    });

    // ============================================
    // PART 4: SWITCH TO ADMIN USER
    // ============================================
    await test.step('Switch to admin user', async () => {
      // Find and click user switcher
      const userMenu = page.getByTestId('user-menu').or(page.locator('[aria-label="User menu"]')).first();
      if (await userMenu.isVisible()) {
        await userMenu.click();
        await page.waitForTimeout(1000);
      }

      // Look for dev user switcher
      const devSwitcher = page.getByTestId('dev-user-switcher').or(page.locator('text=Switch User')).first();
      if (await devSwitcher.isVisible()) {
        await devSwitcher.click();
        await page.waitForTimeout(1000);
      }

      // Alternative: Direct logout and login
      // First logout
      const logoutButton = page.locator('text=Logout').or(page.getByTestId('logout-button')).first();
      if (await logoutButton.isVisible()) {
        await logoutButton.click();
        await page.waitForTimeout(2000);
      }

      // Login as admin
      await page.fill('[data-testid="username-input"]', 'admin_user');
      await page.fill('[data-testid="password-input"]', 'admin123');
      await page.click('[data-testid="login-button"]');

      // Wait for navigation
      await page.waitForURL('**/catalog-explorer', { timeout: 10000 });
      await page.waitForTimeout(2000);
    });

    // ============================================
    // PART 5: NAVIGATE BACK TO THE SAME TABLE
    // ============================================
    await test.step('Navigate back to users table', async () => {
      // Expand arao catalog again
      const araoCatalog = page.locator('text=arao').first();
      await araoCatalog.scrollIntoViewIfNeeded();
      await araoCatalog.click();
      await page.waitForTimeout(2000);

      // Expand metadata_test schema
      const metadataTestSchema = page.locator('text=metadata_test').first();
      await metadataTestSchema.scrollIntoViewIfNeeded();
      await metadataTestSchema.click();
      await page.waitForTimeout(2000);

      // Select users table
      const usersTable = page.locator('text=users').first();
      await usersTable.scrollIntoViewIfNeeded();
      await usersTable.click();
      await page.waitForTimeout(3000);
    });

    // ============================================
    // PART 6: APPROVE THE COMMENT
    // ============================================
    await test.step('Approve the pending comment', async () => {
      // Find the review button for the pending comment
      const reviewButton = page.getByTestId('review-comment-button').first();
      await reviewButton.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // Click review button
      await reviewButton.click();
      await page.waitForTimeout(2000);

      // Wait for review dialog
      await expect(page.getByTestId('review-dialog')).toBeVisible({ timeout: 10000 });

      // Add approval feedback (optional)
      const feedbackInput = page.getByTestId('review-feedback-input');
      if (await feedbackInput.isVisible()) {
        await feedbackInput.fill('Good documentation. Approved for implementation.');
        await page.waitForTimeout(1000);
      }

      // Click approve button
      await page.click('[data-testid="approve-comment-button"]');
      await page.waitForTimeout(2000);

      // Verify the comment status changed
      await expect(page.locator('text=APPROVED').first()).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(2000);
    });

    // ============================================
    // PART 7: APPLY THE COMMENT
    // ============================================
    await test.step('Apply the approved comment', async () => {
      // Find the apply button
      const applyButton = page.getByTestId('apply-comment-button').first();
      await applyButton.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // Click apply button
      await applyButton.click();
      await page.waitForTimeout(3000);

      // Verify the comment has been applied (pending indicator should be gone)
      await expect(page.getByTestId('pending-icon')).not.toBeVisible({ timeout: 10000 });

      // Final wait to show the completed state
      await page.waitForTimeout(3000);
    });

    // ============================================
    // PART 8: FINAL VERIFICATION
    // ============================================
    await test.step('Verify comment is now part of table metadata', async () => {
      // Refresh the page to verify persistence
      await page.reload();
      await page.waitForTimeout(3000);

      // Verify the comment text is visible in the column description
      await expect(page.locator('text=unique identifier for user records')).toBeVisible({ timeout: 10000 });

      // Final pause to show success
      await page.waitForTimeout(3000);
    });
  });
});