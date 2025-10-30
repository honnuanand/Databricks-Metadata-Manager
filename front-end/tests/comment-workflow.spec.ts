import { test, expect } from '@playwright/test';

test.describe('Comment Workflow Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000');
  });

  test.describe('Suggest Only User Workflow', () => {
    test.beforeEach(async ({ page }) => {
      // Login as suggest_only user
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');
      await page.click('[data-testid="login-button"]');
      
      // Wait for login to complete
      await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    });

    test('should create column comment suggestion', async ({ page }) => {
      // Navigate to catalog
      await page.click('[data-testid="nav-catalog"]');
      
      // Navigate to a specific table: arao.metadata_test.users
      await page.click('text=arao');
      await page.click('text=metadata_test');
      await page.click('text=users');
      
      // Wait for table viewer to load
      await expect(page.locator('text=Columns in users')).toBeVisible();
      
      // Find the email column and click the suggest comment button
      const emailRow = page.locator('[data-testid="column-row-email"]');
      await emailRow.locator('[data-testid="suggest-comment-button"]').click();
      
      // Fill in the comment suggestion dialog
      await expect(page.locator('[data-testid="comment-dialog"]')).toBeVisible();
      await page.fill('[data-testid="comment-suggestion-input"]', 'Updated: Primary email address used for user authentication and notifications');
      
      // Submit the suggestion
      await page.click('[data-testid="submit-suggestion-button"]');
      
      // Verify the dialog closes
      await expect(page.locator('[data-testid="comment-dialog"]')).not.toBeVisible();
      
      // Verify the pending comment appears in the table
      await expect(page.locator('text=PENDING')).toBeVisible();
      await expect(page.locator('text=Updated: Primary email address used for user authentication and notifications')).toBeVisible();
    });

    test('should create table comment suggestion', async ({ page }) => {
      // Navigate to catalog and specific table
      await page.click('[data-testid="nav-catalog"]');
      await page.click('text=arao');
      await page.click('text=metadata_test');
      await page.click('text=users');
      
      // Wait for table viewer to load
      await expect(page.locator('text=arao.metadata_test.users')).toBeVisible();
      
      // Click the table comment edit button
      await page.locator('[data-testid="table-comment-edit"]').click();
      
      // Fill in the table comment suggestion
      await expect(page.locator('[data-testid="comment-dialog"]')).toBeVisible();
      await page.fill('[data-testid="comment-suggestion-input"]', 'Updated: Central user management table containing authentication credentials and profile information');
      
      // Submit the suggestion
      await page.click('[data-testid="submit-suggestion-button"]');
      
      // Verify the dialog closes
      await expect(page.locator('[data-testid="comment-dialog"]')).not.toBeVisible();
      
      // Verify the pending table comment appears
      await expect(page.locator('text=Pending table description suggestion')).toBeVisible();
      await expect(page.locator('text=Updated: Central user management table containing authentication credentials and profile information')).toBeVisible();
    });

    test('should create schema comment suggestion', async ({ page }) => {
      // Navigate to catalog
      await page.click('[data-testid="nav-catalog"]');
      await page.click('text=arao');
      
      // Find metadata_test schema and click suggest comment
      const schemaRow = page.locator('[data-testid="schema-metadata_test"]');
      await schemaRow.locator('[data-testid="suggest-comment-button"]').click();
      
      // Fill in the schema comment suggestion
      await expect(page.locator('[data-testid="comment-dialog"]')).toBeVisible();
      await page.fill('[data-testid="comment-suggestion-input"]', 'Test schema containing sample tables for metadata management testing');
      
      // Submit the suggestion
      await page.click('[data-testid="submit-suggestion-button"]');
      
      // Verify the suggestion was created (check My Comments)
      await page.click('[data-testid="nav-my-comments"]');
      await expect(page.locator('text=Test schema containing sample tables for metadata management testing')).toBeVisible();
    });

    test('should navigate from My Comments to specific table', async ({ page }) => {
      // First create a comment (we'll use existing sample data)
      // Navigate to My Comments
      await page.click('[data-testid="nav-my-comments"]');
      
      // Find a comment record and click on the entity path
      const commentRow = page.locator('[data-testid="comment-row"]').first();
      await commentRow.locator('[data-testid="entity-path-link"]').click();
      
      // Verify we navigate to the catalog viewer with the specific table
      await expect(page).toHaveURL(/.*catalog.*catalog=.*schema=.*table=.*/);
      await expect(page.locator('[data-testid="table-viewer"]')).toBeVisible();
    });

    test('should show pending comments in table viewer', async ({ page }) => {
      // Navigate to a table with existing pending comments
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      // Verify pending comments are displayed
      await expect(page.locator('text=PENDING')).toBeVisible();
      await expect(page.locator('[data-testid="pending-comment"]')).toBeVisible();
      
      // Verify visual indicators
      await expect(page.locator('[data-testid="pending-icon"]')).toBeVisible();
      await expect(page.locator('text=by john_suggest')).toBeVisible();
    });
  });

  test.describe('Approver User Workflow', () => {
    test.beforeEach(async ({ page }) => {
      // Login as approver user
      await page.fill('[data-testid="username-input"]', 'jane_approver');
      await page.fill('[data-testid="password-input"]', 'approve123');
      await page.click('[data-testid="login-button"]');
      
      // Wait for login to complete
      await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    });

    test('should see approve and reject options for pending comments', async ({ page }) => {
      // Navigate to a table with pending comments
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      // Verify approver can see review actions
      const emailRow = page.locator('[data-testid="column-row-email"]');
      await expect(emailRow.locator('[data-testid="review-comment-button"]')).toBeVisible();
      await expect(emailRow.locator('[data-testid="apply-comment-button"]')).toBeVisible();
    });

    test('should approve a pending comment', async ({ page }) => {
      // Navigate to pending approvals or table with pending comments
      await page.click('[data-testid="nav-pending-approvals"]');
      
      // Find a pending comment and approve it
      const pendingComment = page.locator('[data-testid="pending-comment-item"]').first();
      await pendingComment.locator('[data-testid="approve-button"]').click();
      
      // Verify approval confirmation
      await expect(page.locator('text=Comment approved successfully')).toBeVisible();
      
      // Verify status change
      await expect(pendingComment.locator('text=APPROVED')).toBeVisible();
    });

    test('should reject a pending comment with feedback', async ({ page }) => {
      // Navigate to pending approvals
      await page.click('[data-testid="nav-pending-approvals"]');
      
      // Find a pending comment and reject it
      const pendingComment = page.locator('[data-testid="pending-comment-item"]').first();
      await pendingComment.locator('[data-testid="reject-button"]').click();
      
      // Fill rejection feedback
      await page.fill('[data-testid="rejection-feedback"]', 'Please be more specific about the data format');
      await page.click('[data-testid="confirm-reject-button"]');
      
      // Verify rejection
      await expect(page.locator('text=Comment rejected')).toBeVisible();
      await expect(pendingComment.locator('text=REJECTED')).toBeVisible();
    });

    test('should request changes for a comment', async ({ page }) => {
      // Navigate to pending approvals
      await page.click('[data-testid="nav-pending-approvals"]');
      
      // Find a pending comment and request changes
      const pendingComment = page.locator('[data-testid="pending-comment-item"]').first();
      await pendingComment.locator('[data-testid="request-changes-button"]').click();
      
      // Fill change request feedback
      await page.fill('[data-testid="change-request-feedback"]', 'Please include information about data validation rules');
      await page.click('[data-testid="confirm-request-changes-button"]');
      
      // Verify change request
      await expect(page.locator('text=Changes requested')).toBeVisible();
      await expect(pendingComment.locator('text=CHANGES_REQUESTED')).toBeVisible();
    });

    test('should batch approve multiple comments', async ({ page }) => {
      // Navigate to pending approvals
      await page.click('[data-testid="nav-pending-approvals"]');
      
      // Select multiple comments
      await page.check('[data-testid="comment-checkbox"]');
      
      // Batch approve
      await page.click('[data-testid="batch-approve-button"]');
      await page.click('[data-testid="confirm-batch-approve"]');
      
      // Verify batch approval
      await expect(page.locator('text=Comments approved successfully')).toBeVisible();
    });
  });

  test.describe('Admin User Workflow', () => {
    test.beforeEach(async ({ page }) => {
      // Login as admin user
      await page.fill('[data-testid="username-input"]', 'admin_user');
      await page.fill('[data-testid="password-input"]', 'admin123');
      await page.click('[data-testid="login-button"]');
      
      // Wait for login to complete
      await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
    });

    test('should apply approved comment to Databricks', async ({ page }) => {
      // Navigate to a table with approved comments
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      // Find an approved comment and apply it
      const emailRow = page.locator('[data-testid="column-row-email"]');
      await emailRow.locator('[data-testid="apply-comment-button"]').click();
      
      // Confirm application
      await page.click('[data-testid="confirm-apply-button"]');
      
      // Verify application success
      await expect(page.locator('text=Comment applied to Databricks successfully')).toBeVisible();
      
      // Verify the comment status changes to APPLIED
      await expect(page.locator('text=APPLIED')).toBeVisible();
    });

    test('should view audit logs for comment changes', async ({ page }) => {
      // Navigate to audit logs
      await page.click('[data-testid="nav-audit-logs"]');
      
      // Verify audit log entries
      await expect(page.locator('[data-testid="audit-log-entry"]')).toBeVisible();
      await expect(page.locator('text=comment_created')).toBeVisible();
      await expect(page.locator('text=comment_approved')).toBeVisible();
      await expect(page.locator('text=comment_applied')).toBeVisible();
    });

    test('should manage users and permissions', async ({ page }) => {
      // Navigate to user management
      await page.click('[data-testid="nav-user-management"]');
      
      // Verify user list
      await expect(page.locator('[data-testid="user-list"]')).toBeVisible();
      await expect(page.locator('text=john_suggest')).toBeVisible();
      await expect(page.locator('text=jane_approver')).toBeVisible();
      
      // Test user permission changes
      const userRow = page.locator('[data-testid="user-row-john_suggest"]');
      await userRow.locator('[data-testid="edit-user-button"]').click();
      
      // Change role
      await page.selectOption('[data-testid="user-role-select"]', 'approver');
      await page.click('[data-testid="save-user-button"]');
      
      // Verify role change
      await expect(page.locator('text=User updated successfully')).toBeVisible();
    });
  });

  test.describe('Role-based Access Control', () => {
    test('suggest_only user cannot approve comments', async ({ page }) => {
      // Login as suggest_only user
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');
      await page.click('[data-testid="login-button"]');
      
      // Navigate to table with pending comments
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      // Verify approve buttons are not visible
      await expect(page.locator('[data-testid="review-comment-button"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="apply-comment-button"]')).not.toBeVisible();
      
      // Verify only suggest button is visible
      await expect(page.locator('[data-testid="suggest-comment-button"]')).toBeVisible();
    });

    test('approver cannot access admin features', async ({ page }) => {
      // Login as approver user
      await page.fill('[data-testid="username-input"]', 'jane_approver');
      await page.fill('[data-testid="password-input"]', 'approve123');
      await page.click('[data-testid="login-button"]');
      
      // Verify admin-only navigation items are not visible
      await expect(page.locator('[data-testid="nav-user-management"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="nav-system-settings"]')).not.toBeVisible();
    });
  });

  test.describe('Error Handling and Edge Cases', () => {
    test('should handle empty comment suggestions', async ({ page }) => {
      // Login and navigate to table
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');
      await page.click('[data-testid="login-button"]');
      
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      // Try to submit empty comment
      const emailRow = page.locator('[data-testid="column-row-email"]');
      await emailRow.locator('[data-testid="suggest-comment-button"]').click();
      
      // Submit without filling
      await page.click('[data-testid="submit-suggestion-button"]');
      
      // Verify submit button is disabled or error message appears
      await expect(page.locator('text=Comment cannot be empty')).toBeVisible();
    });

    test('should handle network errors gracefully', async ({ page }) => {
      // Intercept API calls and simulate network error
      await page.route('**/api/v1/comments', route => {
        route.abort('networkError');
      });
      
      // Login and try to create comment
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');
      await page.click('[data-testid="login-button"]');
      
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      const emailRow = page.locator('[data-testid="column-row-email"]');
      await emailRow.locator('[data-testid="suggest-comment-button"]').click();
      
      await page.fill('[data-testid="comment-suggestion-input"]', 'Test comment');
      await page.click('[data-testid="submit-suggestion-button"]');
      
      // Verify error handling
      await expect(page.locator('text=Failed to submit comment')).toBeVisible();
    });

    test('should handle concurrent comment modifications', async ({ page, context }) => {
      // Create two pages (simulating two users)
      const page2 = await context.newPage();
      
      // Login both users
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');
      await page.click('[data-testid="login-button"]');
      
      await page2.fill('[data-testid="username-input"]', 'alice_suggest');
      await page2.fill('[data-testid="password-input"]', 'suggest123');
      await page2.click('[data-testid="login-button"]');
      
      // Both navigate to same table
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      await page2.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      // Both try to modify same column
      const emailRow1 = page.locator('[data-testid="column-row-email"]');
      const emailRow2 = page2.locator('[data-testid="column-row-email"]');
      
      await emailRow1.locator('[data-testid="suggest-comment-button"]').click();
      await emailRow2.locator('[data-testid="suggest-comment-button"]').click();
      
      // Submit comments simultaneously
      await Promise.all([
        page.fill('[data-testid="comment-suggestion-input"]', 'Comment from user 1'),
        page2.fill('[data-testid="comment-suggestion-input"]', 'Comment from user 2')
      ]);
      
      await Promise.all([
        page.click('[data-testid="submit-suggestion-button"]'),
        page2.click('[data-testid="submit-suggestion-button"]')
      ]);
      
      // Verify both comments are handled appropriately
      await expect(page.locator('text=Comment from user 1')).toBeVisible();
      await expect(page2.locator('text=Comment from user 2')).toBeVisible();
    });
  });

  test.describe('Integration Tests', () => {
    test('complete workflow: suggest -> approve -> apply', async ({ page, context }) => {
      // Step 1: Suggest_only user creates suggestion
      await page.fill('[data-testid="username-input"]', 'john_suggest');
      await page.fill('[data-testid="password-input"]', 'suggest123');
      await page.click('[data-testid="login-button"]');
      
      await page.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      
      const emailRow = page.locator('[data-testid="column-row-email"]');
      await emailRow.locator('[data-testid="suggest-comment-button"]').click();
      await page.fill('[data-testid="comment-suggestion-input"]', 'Integration test: Complete workflow comment');
      await page.click('[data-testid="submit-suggestion-button"]');
      
      // Verify suggestion is created
      await expect(page.locator('text=PENDING')).toBeVisible();
      
      // Step 2: Switch to approver and approve
      const page2 = await context.newPage();
      await page2.goto('http://localhost:3000');
      await page2.fill('[data-testid="username-input"]', 'jane_approver');
      await page2.fill('[data-testid="password-input"]', 'approve123');
      await page2.click('[data-testid="login-button"]');
      
      await page2.click('[data-testid="nav-pending-approvals"]');
      const pendingComment = page2.locator('[data-testid="pending-comment-item"]').first();
      await pendingComment.locator('[data-testid="approve-button"]').click();
      
      // Verify approval
      await expect(page2.locator('text=APPROVED')).toBeVisible();
      
      // Step 3: Switch to admin and apply
      const page3 = await context.newPage();
      await page3.goto('http://localhost:3000');
      await page3.fill('[data-testid="username-input"]', 'admin_user');
      await page3.fill('[data-testid="password-input"]', 'admin123');
      await page3.click('[data-testid="login-button"]');
      
      await page3.goto('http://localhost:3000/catalog?catalog=arao&schema=metadata_test&table=users');
      const emailRow3 = page3.locator('[data-testid="column-row-email"]');
      await emailRow3.locator('[data-testid="apply-comment-button"]').click();
      await page3.click('[data-testid="confirm-apply-button"]');
      
      // Verify application
      await expect(page3.locator('text=APPLIED')).toBeVisible();
      await expect(page3.locator('text=Comment applied to Databricks successfully')).toBeVisible();
    });
  });
});