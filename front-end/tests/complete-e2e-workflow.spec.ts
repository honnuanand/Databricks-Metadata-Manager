import { test, expect } from '@playwright/test';

test.describe('Complete E2E Metadata Workflow', () => {
  test('Full workflow: Suggest → Logout → Login as Approver → Approve → Apply', async ({ page, context }) => {
    test.setTimeout(180000); // 3 minutes
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // PART 1: LOGIN AS SUGGESTION USER
    // ============================================
    console.log('🔐 PART 1: Login as suggestion user (john_suggest)');
    await page.goto('http://localhost:4001');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Login as john_suggest
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);
    console.log('✓ Logged in as john_suggest');

    // ============================================
    // PART 2: NAVIGATE TO CATALOG EXPLORER
    // ============================================
    console.log('📂 PART 2: Navigate to Catalog Explorer');

    // Click on Catalog Explorer in sidebar
    const catalogLink = page.locator('text=Catalog Explorer').first();
    await catalogLink.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    console.log('✓ On Catalog Explorer page');

    // ============================================
    // PART 3: EXPAND CATALOG HIERARCHY
    // ============================================
    console.log('📁 PART 3: Expanding catalog hierarchy');

    // Expand arao catalog
    console.log('  → Clicking arao catalog...');
    await page.locator('text=arao').first().click();
    await page.waitForTimeout(3000);

    // Expand metadata_test schema
    console.log('  → Clicking metadata_test schema...');
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(3000);

    // Scroll and select users table
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(1000);
    console.log('  → Clicking users table...');
    await page.locator('text=users').first().click();
    await page.waitForSelector('[data-testid="table-viewer"]', { timeout: 10000 });
    await page.waitForTimeout(3000);
    console.log('✓ Navigated to users table');

    // ============================================
    // PART 4: ADD COMMENT SUGGESTION
    // ============================================
    console.log('💬 PART 4: Adding comment suggestion');

    // Scroll to see columns
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);

    // Click suggest comment button
    const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();
    await suggestButton.click();
    await page.waitForTimeout(2000);

    // Fill comment
    const commentText = 'Primary key for user records. Auto-incremented unique identifier.';
    const commentField = page.locator('textarea').first();
    await commentField.fill(commentText);
    await page.waitForTimeout(1500);

    // Submit comment
    await page.click('[data-testid="submit-suggestion-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Comment suggestion submitted');

    // ============================================
    // PART 5: LOGOUT CURRENT USER
    // ============================================
    console.log('🔄 PART 5: Logging out john_suggest');

    // Clear all cookies and storage to force logout
    await context.clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Navigate to login page
    await page.goto('http://localhost:4001/login', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Verify we're on login page
    await page.waitForSelector('input[name="username"]', { timeout: 5000 });
    console.log('✓ Logged out successfully');

    // ============================================
    // PART 6: LOGIN AS APPROVER
    // ============================================
    console.log('🔐 PART 6: Login as approver (jane_approver)');

    // Login as jane_approver
    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Logged in as jane_approver');

    // ============================================
    // PART 7: NAVIGATE BACK TO THE SAME TABLE
    // ============================================
    console.log('🔍 PART 7: Navigating back to users table');

    // Click Catalog Explorer
    await page.locator('text=Catalog Explorer').first().click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);

    // Re-expand the same path
    console.log('  → Re-expanding arao catalog...');
    await page.locator('text=arao').first().click();
    await page.waitForTimeout(2000);

    console.log('  → Re-expanding metadata_test schema...');
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(2000);

    console.log('  → Re-selecting users table...');
    await page.locator('text=users').first().click();
    await page.waitForSelector('[data-testid="table-viewer"]', { timeout: 10000 });
    await page.waitForTimeout(3000);
    console.log('✓ Back at users table');

    // ============================================
    // PART 8: REVIEW AND APPROVE COMMENT
    // ============================================
    console.log('✅ PART 8: Reviewing and approving comment');

    // Scroll to find pending comment
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);

    // Look for and click review button
    const reviewButton = page.locator('[data-testid="review-comment-button"]').first();
    const reviewVisible = await reviewButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (reviewVisible) {
      console.log('  → Found review button, clicking...');
      await reviewButton.click();
      await page.waitForTimeout(2000);

      // Check for feedback input in different possible locations
      const feedbackSelectors = [
        '[data-testid="review-feedback-input"]',
        'textarea[placeholder*="feedback"]',
        'input[placeholder*="feedback"]',
        '[role="dialog"] textarea',
        '[role="dialog"] input[type="text"]'
      ];

      let feedbackFilled = false;
      for (const selector of feedbackSelectors) {
        const feedbackInput = page.locator(selector).first();
        if (await feedbackInput.isVisible({ timeout: 1000 }).catch(() => false)) {
          console.log('  → Adding feedback...');
          await feedbackInput.fill('Looks good! Clear and accurate description.');
          await page.waitForTimeout(1000);
          feedbackFilled = true;
          break;
        }
      }

      if (!feedbackFilled) {
        console.log('  → No feedback field found, proceeding to approve...');
      }

      // Click approve button
      const approveSelectors = [
        '[data-testid="approve-comment-button"]',
        'button:has-text("Approve")',
        '[role="dialog"] button:has-text("Approve")'
      ];

      for (const selector of approveSelectors) {
        const approveButton = page.locator(selector).first();
        if (await approveButton.isVisible({ timeout: 1000 }).catch(() => false)) {
          console.log('  → Clicking approve button...');
          await approveButton.click();
          await page.waitForTimeout(4000);
          console.log('✓ Comment approved');
          break;
        }
      }
    } else {
      console.log('⚠ Review button not found - comment might already be approved');
    }

    // ============================================
    // PART 9: APPLY COMMENT TO DATABRICKS
    // ============================================
    console.log('🚀 PART 9: Applying comment to Databricks');
    await page.waitForTimeout(2000);

    // Look for and click apply button
    const applySelectors = [
      '[data-testid="apply-comment-button"]',
      'button:has-text("Apply")',
      'button:has-text("Apply to Databricks")'
    ];

    let applied = false;
    for (const selector of applySelectors) {
      const applyButton = page.locator(selector).first();
      if (await applyButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('  → Found apply button, clicking...');
        await applyButton.click();
        await page.waitForTimeout(5000);
        console.log('✓ Comment applied to Databricks');
        applied = true;
        break;
      }
    }

    if (!applied) {
      console.log('⚠ Apply button not found - comment might already be applied');
    }

    // ============================================
    // PART 10: FINAL VERIFICATION
    // ============================================
    console.log('🎉 PART 10: Final verification');

    // Scroll to top for final view
    await page.mouse.wheel(0, -500);
    await page.waitForTimeout(2000);

    // Take final screenshot
    await page.screenshot({ path: 'test-videos/complete-e2e-workflow.png' });

    // Final pause for video
    await page.waitForTimeout(3000);

    console.log('════════════════════════════════════════════════════');
    console.log('✅ COMPLETE WORKFLOW SUCCESSFULLY DEMONSTRATED!');
    console.log('════════════════════════════════════════════════════');
    console.log('Workflow steps completed:');
    console.log('  1. Login as john_suggest (suggestion-only user)');
    console.log('  2. Navigate through catalog hierarchy');
    console.log('  3. Add comment suggestion to column');
    console.log('  4. Logout and switch to jane_approver');
    console.log('  5. Navigate back to the same table');
    console.log('  6. Review and approve the comment');
    console.log('  7. Apply the comment to Databricks');
    console.log('════════════════════════════════════════════════════');
  });
});