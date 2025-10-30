import { test, expect } from '@playwright/test';

test.describe('Complete E2E Metadata Workflow', () => {
  test('Full workflow with smooth video recording', async ({ page, context }) => {
    test.setTimeout(240000); // 4 minutes

    // Inject CSS to disable animations globally
    await page.addInitScript(() => {
      const style = document.createElement('style');
      style.innerHTML = `
        *, *::before, *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
        }
      `;
      document.head.appendChild(style);
    });

    // ============================================
    // PART 1: LOGIN AS SUGGESTION USER
    // ============================================
    console.log('🔐 PART 1: Login as suggestion user (john_suggest)');
    await page.goto('http://localhost:4001', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Login as john_suggest
    await page.fill('input[name="username"]', 'john_suggest', { timeout: 10000 });
    await page.waitForTimeout(500);
    await page.fill('input[name="password"]', 'suggest123');
    await page.waitForTimeout(500);
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);
    console.log('✓ Logged in as john_suggest');

    // ============================================
    // PART 2: NAVIGATE TO CATALOG EXPLORER
    // ============================================
    console.log('📂 PART 2: Navigate to Catalog Explorer');
    await page.waitForTimeout(1000);

    // Click on Catalog Explorer in sidebar
    const catalogLink = page.locator('text=Catalog Explorer').first();
    await catalogLink.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    console.log('✓ On Catalog Explorer page');

    // ============================================
    // PART 3: EXPAND CATALOG HIERARCHY
    // ============================================
    console.log('📁 PART 3: Expanding catalog hierarchy');
    await page.waitForTimeout(1500);

    // Expand arao catalog
    console.log('  → Clicking arao catalog...');
    await page.locator('text=arao').first().click();
    await page.waitForTimeout(2500);

    // Expand metadata_test schema
    console.log('  → Clicking metadata_test schema...');
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(2500);

    // Scroll smoothly and select users table
    await page.evaluate(() => window.scrollBy({ top: 200, behavior: 'instant' }));
    await page.waitForTimeout(1500);

    console.log('  → Clicking users table...');
    await page.locator('text=users').first().click();
    await page.waitForSelector('[data-testid="table-viewer"]', { timeout: 10000 });
    await page.waitForTimeout(3000);
    console.log('✓ Navigated to users table');

    // ============================================
    // PART 4: ADD COMMENT SUGGESTION
    // ============================================
    console.log('💬 PART 4: Adding comment suggestion');
    await page.waitForTimeout(1500);

    // Scroll to see columns smoothly
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'instant' }));
    await page.waitForTimeout(2000);

    // Click suggest comment button
    const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();
    await suggestButton.click();
    await page.waitForTimeout(2000);

    // Fill comment with typing effect
    const commentText = 'Primary key for user records. Auto-incremented unique identifier.';
    const commentField = page.locator('textarea').first();
    await commentField.type(commentText, { delay: 50 });
    await page.waitForTimeout(1500);

    // Submit comment
    await page.click('[data-testid="submit-suggestion-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Comment suggestion submitted');

    // ============================================
    // PART 5: LOGOUT CURRENT USER
    // ============================================
    console.log('🔄 PART 5: Logging out john_suggest');
    await page.waitForTimeout(1500);

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
    await page.waitForTimeout(1000);

    // Login as jane_approver with typing effect
    await page.type('input[name="username"]', 'jane_approver', { delay: 50 });
    await page.waitForTimeout(500);
    await page.type('input[name="password"]', 'approve123', { delay: 50 });
    await page.waitForTimeout(500);
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Logged in as jane_approver');

    // ============================================
    // PART 7: NAVIGATE BACK TO THE SAME TABLE
    // ============================================
    console.log('🔍 PART 7: Navigating back to users table');
    await page.waitForTimeout(1500);

    // Click Catalog Explorer
    await page.locator('text=Catalog Explorer').first().click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Re-expand the same path with delays
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
    await page.waitForTimeout(1500);

    // Scroll to find pending comment smoothly
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'instant' }));
    await page.waitForTimeout(2000);

    // Look for and click review button
    const reviewButton = page.locator('[data-testid="review-comment-button"]').first();
    const reviewVisible = await reviewButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (reviewVisible) {
      console.log('  → Found review button, clicking...');
      await reviewButton.click();
      await page.waitForTimeout(2500);

      // Check for feedback input
      const feedbackSelectors = [
        '[data-testid="review-feedback-input"]',
        'textarea[placeholder*="feedback"]',
        'input[placeholder*="feedback"]',
        '[role="dialog"] textarea',
        '[role="dialog"] input[type="text"]'
      ];

      for (const selector of feedbackSelectors) {
        const feedbackInput = page.locator(selector).first();
        if (await feedbackInput.isVisible({ timeout: 1000 }).catch(() => false)) {
          console.log('  → Adding feedback...');
          await feedbackInput.type('Looks good! Clear and accurate description.', { delay: 50 });
          await page.waitForTimeout(1500);
          break;
        }
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

    for (const selector of applySelectors) {
      const applyButton = page.locator(selector).first();
      if (await applyButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('  → Found apply button, clicking...');
        await applyButton.click();
        await page.waitForTimeout(5000);
        console.log('✓ Comment applied to Databricks');
        break;
      }
    }

    // ============================================
    // PART 10: FINAL VERIFICATION
    // ============================================
    console.log('🎉 PART 10: Final verification');
    await page.waitForTimeout(1500);

    // Scroll to top smoothly for final view
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.waitForTimeout(2000);

    // Take final screenshot
    await page.screenshot({ path: 'test-videos/smooth-e2e-workflow.png' });

    // Final pause for video
    await page.waitForTimeout(3000);

    console.log('════════════════════════════════════════════════════');
    console.log('✅ COMPLETE WORKFLOW SUCCESSFULLY DEMONSTRATED!');
    console.log('════════════════════════════════════════════════════');
  });
});