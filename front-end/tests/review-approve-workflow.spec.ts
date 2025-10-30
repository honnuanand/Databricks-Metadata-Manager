import { test, expect } from '@playwright/test';

test.describe('Review and Approve Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:4001');
  });

  test('approver can review and approve a pending comment', async ({ page }) => {
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Find a column with pending comments and click review button
    const emailRow = page.locator('[data-testid="column-row-email"]');
    
    // Wait for pending comments to load
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    
    // Click the review button
    await emailRow.locator('[data-testid="review-comment-button"]').click();
    
    // Verify review dialog opens
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    
    // Verify dialog shows comment details
    await expect(page.locator('text=Comment Details:')).toBeVisible();
    await expect(page.locator('text=Suggested Comment:')).toBeVisible();
    await expect(page.locator('text=john_suggest')).toBeVisible();
    
    // Add optional feedback
    await page.fill('[data-testid="review-feedback-input"]', 'Great suggestion! This provides much better clarity.');
    
    // Approve the comment
    await page.click('[data-testid="approve-comment-button"]');
    
    // Verify dialog closes
    await expect(page.locator('[data-testid="review-dialog"]')).not.toBeVisible();
    
    // Verify the comment status changes to approved
    await expect(page.locator('text=APPROVED')).toBeVisible({ timeout: 10000 });
  });

  test('approver can reject a comment with feedback', async ({ page }) => {
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=products');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Find the price column and click review button
    const priceRow = page.locator('[data-testid="column-row-price"]');
    
    // Wait for pending comments to load
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    
    // Click the review button
    await priceRow.locator('[data-testid="review-comment-button"]').click();
    
    // Verify review dialog opens
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    
    // Add rejection feedback
    await page.fill('[data-testid="review-feedback-input"]', 'Please be more specific about the currency and include information about tax calculations.');
    
    // Reject the comment
    await page.click('[data-testid="reject-comment-button"]');
    
    // Verify dialog closes
    await expect(page.locator('[data-testid="review-dialog"]')).not.toBeVisible();
    
    // Verify the comment status changes to rejected
    await expect(page.locator('text=REJECTED')).toBeVisible({ timeout: 10000 });
  });

  test('rejection requires feedback', async ({ page }) => {
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Find a column with pending comments and click review button
    const emailRow = page.locator('[data-testid="column-row-email"]');
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    await emailRow.locator('[data-testid="review-comment-button"]').click();
    
    // Verify review dialog opens
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    
    // Try to reject without feedback - button should be disabled
    await expect(page.locator('[data-testid="reject-comment-button"]')).toBeDisabled();
    
    // Add feedback and verify button becomes enabled
    await page.fill('[data-testid="review-feedback-input"]', 'Need more details');
    await expect(page.locator('[data-testid="reject-comment-button"]')).toBeEnabled();
  });

  test('approval works without feedback', async ({ page }) => {
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Find a column with pending comments and click review button
    const emailRow = page.locator('[data-testid="column-row-email"]');
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    await emailRow.locator('[data-testid="review-comment-button"]').click();
    
    // Verify review dialog opens
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    
    // Approve without adding feedback
    await page.click('[data-testid="approve-comment-button"]');
    
    // Verify dialog closes and status changes
    await expect(page.locator('[data-testid="review-dialog"]')).not.toBeVisible();
    await expect(page.locator('text=APPROVED')).toBeVisible({ timeout: 10000 });
  });

  test('suggest_only user cannot see review buttons', async ({ page }) => {
    // Login as suggest_only user
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Verify review buttons are not visible for suggest_only user
    await expect(page.locator('[data-testid="review-comment-button"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="apply-comment-button"]')).not.toBeVisible();
    
    // But suggest button should be visible
    await expect(page.locator('[data-testid="suggest-comment-button"]').first()).toBeVisible();
  });

  test('admin can approve and apply comments', async ({ page }) => {
    // Login as admin
    await page.fill('[data-testid="username-input"]', 'admin_user');
    await page.fill('[data-testid="password-input"]', 'admin123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Verify admin can see all action buttons
    await expect(page.locator('[data-testid="suggest-comment-button"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="review-comment-button"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="apply-comment-button"]').first()).toBeVisible();
    
    // Test approval workflow
    const emailRow = page.locator('[data-testid="column-row-email"]');
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    await emailRow.locator('[data-testid="review-comment-button"]').click();
    
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    await page.click('[data-testid="approve-comment-button"]');
    await expect(page.locator('[data-testid="review-dialog"]')).not.toBeVisible();
    
    // Verify approval and that apply button becomes actionable
    await expect(page.locator('text=APPROVED')).toBeVisible({ timeout: 10000 });
  });

  test('review dialog shows complete comment information', async ({ page }) => {
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Open review dialog
    const emailRow = page.locator('[data-testid="column-row-email"]');
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    await emailRow.locator('[data-testid="review-comment-button"]').click();
    
    // Verify all required information is displayed
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    
    // Check entity information
    await expect(page.locator('text=arao.metadata_test.users.email')).toBeVisible();
    
    // Check author information
    await expect(page.locator('text=john_suggest')).toBeVisible();
    
    // Check current comment (if any)
    await expect(page.locator('text=Current Comment:')).toBeVisible();
    
    // Check suggested comment
    await expect(page.locator('text=Suggested Comment:')).toBeVisible();
    await expect(page.locator('text=Primary email address for user communication and authentication')).toBeVisible();
    
    // Check feedback input
    await expect(page.locator('[data-testid="review-feedback-input"]')).toBeVisible();
    
    // Check action buttons
    await expect(page.locator('[data-testid="approve-comment-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="reject-comment-button"]')).toBeVisible();
  });

  test('multiple pending comments can be reviewed independently', async ({ page }) => {
    // This test assumes we have multiple pending comments for different columns
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with multiple pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Count pending comments
    const pendingComments = page.locator('[data-testid="pending-comment"]');
    const count = await pendingComments.count();
    
    if (count > 0) {
      // Verify multiple review buttons are available
      const reviewButtons = page.locator('[data-testid="review-comment-button"]');
      const buttonCount = await reviewButtons.count();
      expect(buttonCount).toBeGreaterThan(0);
      
      // Test reviewing one comment doesn't affect others
      await reviewButtons.first().click();
      await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
      
      // Cancel and verify others are still available
      await page.click('text=Cancel');
      await expect(page.locator('[data-testid="review-dialog"]')).not.toBeVisible();
      
      // Verify review buttons are still available
      await expect(reviewButtons.first()).toBeVisible();
    }
  });

  test('error handling for approval workflow', async ({ page }) => {
    // Login as approver
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Intercept API calls and simulate errors
    await page.route('**/api/v1/approvals/*/approve', route => {
      route.abort('networkError');
    });
    
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Try to approve a comment
    const emailRow = page.locator('[data-testid="column-row-email"]');
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    await emailRow.locator('[data-testid="review-comment-button"]').click();
    
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
    await page.click('[data-testid="approve-comment-button"]');
    
    // Dialog should remain open due to error (though error handling could show a toast)
    // In a real implementation, you might want to show an error message
    await expect(page.locator('[data-testid="review-dialog"]')).toBeVisible();
  });
});