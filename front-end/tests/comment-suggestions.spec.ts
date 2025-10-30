import { test, expect } from '@playwright/test';

test.describe('Comment Suggestions Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:4001');
  });

  test('suggest_only user can create column comment suggestion', async ({ page }) => {
    // Login as suggest_only user
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    
    // Wait for login to complete
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to catalog explorer
    await page.click('[data-testid="nav-catalog-explorer"]');
    
    // Navigate to the test table with URL parameters
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    
    // Wait for table viewer to load
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Find the email column row and click suggest comment
    const emailRow = page.locator('[data-testid="column-row-email"]');
    await emailRow.locator('[data-testid="suggest-comment-button"]').click();
    
    // Verify comment dialog opens
    await expect(page.locator('[data-testid="comment-dialog"]')).toBeVisible();
    
    // Fill in the comment suggestion
    const testComment = 'Test suggestion: Primary email address for user authentication and notifications';
    await page.fill('[data-testid="comment-suggestion-input"]', testComment);
    
    // Submit the suggestion
    await page.click('[data-testid="submit-suggestion-button"]');
    
    // Verify the dialog closes
    await expect(page.locator('[data-testid="comment-dialog"]')).not.toBeVisible();
    
    // Verify the pending comment appears in the table (wait for it)
    await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=PENDING')).toBeVisible();
    await expect(page.locator(`text=${testComment}`)).toBeVisible();
  });

  test('suggest_only user can create table comment suggestion', async ({ page }) => {
    // Login
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Click table comment edit button
    await page.click('[data-testid="table-comment-edit"]');
    
    // Fill in table comment
    const testComment = 'Test table comment: Core user management table with authentication data';
    await page.fill('[data-testid="comment-suggestion-input"]', testComment);
    await page.click('[data-testid="submit-suggestion-button"]');
    
    // Verify dialog closes and pending comment appears
    await expect(page.locator('[data-testid="comment-dialog"]')).not.toBeVisible();
    await expect(page.locator('text=Pending table description suggestion')).toBeVisible({ timeout: 10000 });
    await expect(page.locator(`text=${testComment}`)).toBeVisible();
  });

  test('navigation from My Comments to catalog viewer works', async ({ page }) => {
    // Login
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Go to My Comments
    await page.click('[data-testid="nav-my-comments"]');
    
    // Look for entity path links (using existing sample data)
    const entityLinks = page.locator('button:has-text("arao.metadata_test")');
    if (await entityLinks.count() > 0) {
      await entityLinks.first().click();
      
      // Verify navigation to catalog viewer
      await expect(page).toHaveURL(/.*catalog.*catalog=.*schema=.*table=.*/);
      await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    }
  });

  test('pending comments are visible with correct indicators', async ({ page }) => {
    // Login
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Navigate to table with existing pending comments
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Check for existing pending comments from sample data
    const pendingComments = page.locator('[data-testid="pending-comment"]');
    if (await pendingComments.count() > 0) {
      // Verify pending indicators are visible
      await expect(page.locator('[data-testid="pending-icon"]').first()).toBeVisible();
      await expect(page.locator('text=PENDING').first()).toBeVisible();
      await expect(page.locator('text=by john_suggest').first()).toBeVisible();
    }
  });

  test('role-based access control works correctly', async ({ page }) => {
    // Test suggest_only user permissions
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Verify suggest_only user can see suggest button but not approve/apply buttons
    await expect(page.locator('[data-testid="suggest-comment-button"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="review-comment-button"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="apply-comment-button"]')).not.toBeVisible();
    
    // Test approver user permissions
    await page.click('[data-testid="user-profile"]');
    await page.click('text=Logout');
    
    await page.fill('[data-testid="username-input"]', 'jane_approver');
    await page.fill('[data-testid="password-input"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    await page.goto('http://localhost:4001/catalog?catalog=arao&schema=metadata_test&table=users');
    await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    
    // Verify approver can see all buttons
    await expect(page.locator('[data-testid="suggest-comment-button"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="review-comment-button"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="apply-comment-button"]').first()).toBeVisible();
  });

  test('user switching works correctly', async ({ page }) => {
    // Start with suggest_only user
    await page.fill('[data-testid="username-input"]', 'john_suggest');
    await page.fill('[data-testid="password-input"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    
    // Verify current user role
    await expect(page.locator('text=SUGGEST ONLY')).toBeVisible();
    
    // Use the dev user switcher (floating action button)
    if (await page.locator('[data-testid="dev-user-switcher"]').isVisible()) {
      await page.click('[data-testid="dev-user-switcher"]');
      await page.click('text=Jane Smith'); // Switch to approver
      
      // Verify user switched
      await expect(page.locator('text=APPROVER')).toBeVisible();
    }
  });
});