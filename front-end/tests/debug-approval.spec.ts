import { test, expect } from '@playwright/test';

test.describe('Debug Approval Button', () => {
  test('Check comment status and button state', async ({ page }) => {
    test.setTimeout(120000);

    // Login as suggest user and create a comment
    console.log('Step 1: Login as john_suggest');
    await page.goto('http://localhost:4001');
    await page.waitForLoadState('networkidle');

    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);

    // Navigate to catalog
    console.log('Step 2: Navigate to a table');
    await page.locator('text=Catalog Explorer').first().click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Expand catalog and schema
    await page.locator('text=arao').first().click();
    await page.waitForTimeout(2000);
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(2000);
    await page.locator('text=products').first().click();
    await page.waitForTimeout(3000);

    // Add a comment suggestion
    console.log('Step 3: Add comment suggestion');
    const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();
    await suggestButton.click();
    await page.waitForTimeout(1000);

    const commentField = page.locator('textarea').first();
    await commentField.fill('Test comment for debugging approval workflow');
    await page.waitForTimeout(500);

    await page.click('[data-testid="submit-suggestion-button"]');
    await page.waitForTimeout(3000);

    // Intercept API call to see comment data
    await page.route('**/api/comments/**', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      console.log('API Response:', JSON.stringify(json, null, 2));
      await route.fulfill({ response });
    });

    // Logout and login as approver
    console.log('Step 4: Switch to approver user');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto('http://localhost:4001/login');
    await page.waitForTimeout(2000);

    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);

    // Navigate back to the same table
    console.log('Step 5: Navigate to table as approver');
    await page.locator('text=Catalog Explorer').first().click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    await page.locator('text=arao').first().click();
    await page.waitForTimeout(2000);
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(2000);
    await page.locator('text=products').first().click();
    await page.waitForTimeout(3000);

    // Check console logs
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Fetched pending comments:') ||
          text.includes('getColumnPendingComments') ||
          text.includes('Review button for')) {
        console.log('BROWSER LOG:', text);
      }
    });

    // Force a re-render to trigger logs
    await page.reload();
    await page.waitForTimeout(5000);

    // Check if review buttons exist
    const reviewButtons = await page.locator('[data-testid="review-comment-button"]').count();
    console.log(`Found ${reviewButtons} review buttons`);

    // Check if any are enabled
    const enabledButtons = await page.locator('[data-testid="review-comment-button"]:not([disabled])').count();
    console.log(`Found ${enabledButtons} enabled review buttons`);

    // Take a screenshot
    await page.screenshot({ path: 'test-videos/debug-approval-buttons.png', fullPage: true });

    console.log('Test complete - check console output above');
  });
});