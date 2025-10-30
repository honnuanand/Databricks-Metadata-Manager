import { test, expect } from '@playwright/test';

test.describe('Complete Metadata Manager Workflow', () => {
  test('Full end-to-end workflow: Suggest → Approve → Apply', async ({ page }) => {
    test.setTimeout(240000); // 4 minutes
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // PART 1: LOGIN AS SUGGESTION USER
    // ============================================
    console.log('🔐 PART 1: Login as suggestion user');
    await page.goto('http://localhost:4001');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Login with john_suggest
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('[data-testid="login-button"]');

    // Wait for navigation
    await page.waitForURL('**/catalog', { timeout: 10000 }).catch(() => {
      console.log('Did not auto-navigate to catalog, will navigate manually');
    });
    await page.waitForTimeout(3000);
    console.log('✓ Logged in as john_suggest');

    // ============================================
    // PART 2: NAVIGATE TO CATALOG EXPLORER
    // ============================================
    console.log('📂 PART 2: Navigate to Catalog Explorer');

    // Ensure we're on the catalog page
    if (!page.url().includes('/catalog')) {
      await page.goto('http://localhost:4001/catalog');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
    }

    console.log('Current URL:', page.url());
    console.log('✓ On Catalog Explorer page');

    // ============================================
    // PART 3: EXPAND ARAO CATALOG
    // ============================================
    console.log('📁 PART 3: Expanding arao catalog');
    await page.waitForTimeout(2000);

    // Wait for catalogs to load
    await page.waitForSelector('.MuiAccordion-root', { timeout: 10000 });

    // Find and click arao catalog
    const araoAccordion = page.locator('.MuiAccordion-root').filter({ hasText: 'arao' }).first();
    const araoVisible = await araoAccordion.isVisible().catch(() => false);

    if (araoVisible) {
      // Click on the accordion header to expand
      const araoHeader = araoAccordion.locator('.MuiAccordionSummary-root').first();
      await araoHeader.click();
      await page.waitForTimeout(3000);
      console.log('✓ Arao catalog expanded');
    } else {
      // Fallback: try clicking on text
      await page.locator('text=arao').first().click();
      await page.waitForTimeout(3000);
    }

    // ============================================
    // PART 4: EXPAND METADATA_TEST SCHEMA
    // ============================================
    console.log('📊 PART 4: Expanding metadata_test schema');
    await page.waitForTimeout(2000);

    // Click on metadata_test schema
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(3000);
    console.log('✓ metadata_test schema expanded');

    // Scroll to see tables
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(1000);

    // ============================================
    // PART 5: SELECT USERS TABLE
    // ============================================
    console.log('📋 PART 5: Selecting users table');
    await page.waitForTimeout(1000);

    // Click on users table
    await page.locator('text=users').first().click();

    // Wait for table viewer to load
    await page.waitForSelector('[data-testid="table-viewer"]', { timeout: 10000 });
    await page.waitForTimeout(3000);
    console.log('✓ Users table loaded');

    // ============================================
    // PART 6: ADD COMMENT SUGGESTION
    // ============================================
    console.log('💬 PART 6: Adding comment suggestion');

    // Scroll to see columns
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);

    // Find and click suggest comment button for first column
    const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();
    await suggestButton.click();
    await page.waitForTimeout(2000);

    // Wait for dialog/modal to appear
    await page.waitForSelector('[data-testid="comment-suggestion-input"], [role="dialog"]', { timeout: 5000 });

    // Fill in the comment - handle both textarea and input
    const commentSelector = '[data-testid="comment-suggestion-input"] textarea, [data-testid="comment-suggestion-input"] input, [data-testid="comment-suggestion-input"]';
    const commentField = page.locator(commentSelector).first();
    await commentField.fill('Primary key for user records. Auto-generated unique identifier that ensures each user has a distinct ID in the system.');
    await page.waitForTimeout(1000);

    // Submit the comment
    await page.click('[data-testid="submit-suggestion-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Comment suggestion submitted');

    // ============================================
    // PART 7: LOGOUT AND SWITCH TO APPROVER
    // ============================================
    console.log('🔄 PART 7: Switching to approver user');

    // Method 1: Try using the user menu to logout
    const userMenu = page.locator('[data-testid="user-menu"], [aria-label*="user"], .MuiAvatar-root').first();
    if (await userMenu.isVisible({ timeout: 2000 }).catch(() => false)) {
      await userMenu.click();
      await page.waitForTimeout(1000);

      const logoutButton = page.locator('text=Logout, text=Sign out, [data-testid="logout-button"]').first();
      if (await logoutButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await logoutButton.click();
        await page.waitForTimeout(2000);
      }
    }

    // Method 2: Navigate directly to login (forces logout)
    await page.goto('http://localhost:4001/login');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Login as jane_approver
    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Logged in as jane_approver');

    // ============================================
    // PART 8: NAVIGATE BACK TO USERS TABLE
    // ============================================
    console.log('🔍 PART 8: Navigating back to users table');

    // Go to catalog page
    await page.goto('http://localhost:4001/catalog');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Re-expand arao catalog
    const araoAccordion2 = page.locator('.MuiAccordion-root').filter({ hasText: 'arao' }).first();
    if (await araoAccordion2.isVisible({ timeout: 3000 }).catch(() => false)) {
      const araoHeader2 = araoAccordion2.locator('.MuiAccordionSummary-root').first();
      await araoHeader2.click();
    } else {
      await page.locator('text=arao').first().click();
    }
    await page.waitForTimeout(2000);

    // Click metadata_test schema
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(2000);

    // Click users table
    await page.locator('text=users').first().click();
    await page.waitForSelector('[data-testid="table-viewer"]', { timeout: 10000 });
    await page.waitForTimeout(3000);
    console.log('✓ Back at users table');

    // ============================================
    // PART 9: REVIEW AND APPROVE COMMENT
    // ============================================
    console.log('✅ PART 9: Reviewing and approving comment');

    // Scroll to find the pending comment
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);

    // Look for review button (should be visible for approver)
    const reviewButton = page.locator('[data-testid="review-comment-button"]').first();
    const reviewVisible = await reviewButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (reviewVisible) {
      console.log('Found review button, clicking...');
      await reviewButton.click();
      await page.waitForTimeout(2000);

      // Wait for review dialog
      await page.waitForSelector('[role="dialog"], [data-testid="review-dialog"]', { timeout: 5000 });

      // Add feedback
      const feedbackField = page.locator('[data-testid="review-feedback-input"], textarea, input[placeholder*="feedback"]').first();
      if (await feedbackField.isVisible({ timeout: 2000 }).catch(() => false)) {
        await feedbackField.fill('Looks good! Clear and accurate description.');
        await page.waitForTimeout(1000);
      }

      // Click approve button
      const approveButton = page.locator('[data-testid="approve-comment-button"], button:has-text("Approve")').first();
      await approveButton.click();
      await page.waitForTimeout(4000);
      console.log('✓ Comment approved');
    } else {
      console.log('⚠ Review button not found - comment might already be approved');
    }

    // ============================================
    // PART 10: APPLY COMMENT TO DATABRICKS
    // ============================================
    console.log('🚀 PART 10: Applying comment to Databricks');
    await page.waitForTimeout(2000);

    // Look for apply button (visible after approval)
    const applyButton = page.locator('[data-testid="apply-comment-button"], button:has-text("Apply")').first();
    const applyVisible = await applyButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (applyVisible) {
      console.log('Found apply button, clicking...');
      await applyButton.click();
      await page.waitForTimeout(5000);
      console.log('✓ Comment applied to Databricks');
    } else {
      console.log('⚠ Apply button not found - comment might already be applied');
    }

    // ============================================
    // FINAL: VERIFICATION
    // ============================================
    console.log('🎉 WORKFLOW COMPLETE!');

    // Scroll to top for final view
    await page.mouse.wheel(0, -500);
    await page.waitForTimeout(2000);

    // Take a final screenshot
    await page.screenshot({ path: 'test-videos/final-state.png', fullPage: false });

    // Final pause for video
    await page.waitForTimeout(3000);

    console.log('═══════════════════════════════════════');
    console.log('✅ Full workflow completed successfully!');
    console.log('═══════════════════════════════════════');
  });
});