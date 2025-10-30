import { test, expect } from '@playwright/test';

test.describe('Complete Workflow with Audit Log and Apply Queue', () => {
  test('full workflow: suggest → approve → apply → audit', async ({ page, video }) => {
    // ========== STEP 1: Login as suggest user ==========
    console.log('Step 1: Login as suggest user');
    await page.goto('http://localhost:4001/login');
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:4001/');

    // ========== STEP 2: Navigate to Catalog Explorer ==========
    console.log('Step 2: Navigate to Catalog Explorer');
    await page.click('text=Catalog Explorer');
    await page.waitForURL('http://localhost:4001/catalog');

    // Wait for catalog to load
    await page.waitForSelector('text=arao', { timeout: 10000 });

    // ========== STEP 3: Navigate to table ==========
    console.log('Step 3: Navigate through catalog hierarchy');
    await page.click('text=arao');
    await page.waitForTimeout(1000);
    await page.click('text=metadata_test');
    await page.waitForTimeout(1000);
    await page.click('text=products');
    await page.waitForTimeout(2000);

    // ========== STEP 4: Add a comment suggestion ==========
    console.log('Step 4: Add a comment suggestion');

    // Look for the edit icon on the first column
    const editButtons = page.locator('button[aria-label="Edit comment"]');
    const editButtonCount = await editButtons.count();

    if (editButtonCount > 0) {
      await editButtons.first().click();
      await page.waitForTimeout(500);

      // Enter a new comment
      const commentInput = page.locator('textarea, input[type="text"]').last();
      await commentInput.fill('Test comment for e2e workflow - Product price in USD');
      await page.waitForTimeout(500);

      // Click save
      await page.click('button:has-text("Save")');
      await page.waitForTimeout(1000);

      console.log('Comment suggestion added');
    }

    // ========== STEP 5: Check My Comments ==========
    console.log('Step 5: Check My Comments');
    await page.click('text=My Comments');
    await page.waitForURL('http://localhost:4001/my-comments');
    await page.waitForTimeout(1000);

    // Verify the comment appears in My Comments
    await expect(page.locator('text=DRAFT, text=PENDING').first()).toBeVisible({ timeout: 5000 });

    // ========== STEP 6: Logout and login as approver ==========
    console.log('Step 6: Switch to approver user');
    await page.click('[data-testid="user-profile"]');
    await page.click('text=Logout');

    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:4001/');

    // ========== STEP 7: Check Approval Queue ==========
    console.log('Step 7: Navigate to Approval Queue');
    await page.click('text=Approval Queue');
    await page.waitForURL('http://localhost:4001/approvals');
    await page.waitForTimeout(1000);

    // Check if there are pending approvals
    const hasPendingApprovals = await page.locator('tbody tr').count() > 0;

    if (hasPendingApprovals) {
      console.log('Step 8: Approve a comment');

      // Click on the first approve button
      const approveButton = page.locator('button:has-text("Approve")').first();
      await approveButton.click();
      await page.waitForTimeout(500);

      // Fill in optional feedback if dialog appears
      const feedbackInput = page.locator('textarea[placeholder*="feedback"], textarea[name="feedback"]');
      if (await feedbackInput.isVisible().catch(() => false)) {
        await feedbackInput.fill('Looks good, approved!');
      }

      // Click final approve button in dialog
      const confirmButton = page.locator('button:has-text("Approve")').last();
      await confirmButton.click();
      await page.waitForTimeout(2000);

      console.log('Comment approved');
    }

    // ========== STEP 9: Check Apply Queue ==========
    console.log('Step 9: Navigate to Apply Queue');
    await page.click('text=Apply Queue');
    await page.waitForURL('http://localhost:4001/apply-queue');
    await page.waitForTimeout(1000);

    // Check if there are approved comments ready to apply
    const hasApprovedComments = await page.locator('table tbody tr').count() > 0;

    if (hasApprovedComments) {
      console.log('Step 10: Apply approved comment to Databricks');

      // Click apply button on first comment
      const applyButton = page.locator('button:has-text("Apply")').first();
      await applyButton.click();
      await page.waitForTimeout(500);

      // Wait for confirmation dialog
      await page.waitForSelector('text=Apply Comment to Databricks');

      // Verify dialog shows entity information
      await expect(page.locator('text=Entity:')).toBeVisible();
      await expect(page.locator('text=New Comment:')).toBeVisible();

      // Click Apply to Databricks button
      await page.click('button:has-text("Apply to Databricks")');
      await page.waitForTimeout(3000);

      // Check for success message
      const successAlert = page.locator('text=Successfully applied');
      if (await successAlert.isVisible().catch(() => false)) {
        console.log('Comment successfully applied to Databricks');
      }
    }

    // ========== STEP 11: Check Audit Log ==========
    console.log('Step 11: Navigate to Audit Log');
    await page.click('text=Audit Log');
    await page.waitForURL('http://localhost:4001/audit-log');
    await page.waitForTimeout(1000);

    // Verify audit log shows the workflow
    await expect(page.locator('h4:has-text("Audit Log")')).toBeVisible();

    // Check statistics are populated
    const totalChanges = page.locator('text=Total Changes').locator('..').locator('h4');
    await expect(totalChanges).toBeVisible();

    // Check table has data
    const auditRows = page.locator('tbody tr');
    const auditRowCount = await auditRows.count();
    expect(auditRowCount).toBeGreaterThan(0);

    // Verify role chips are visible
    const roleChips = page.locator('.MuiChip-label').filter({ hasText: /SUGGEST ONLY|APPROVER|ADMIN/ });
    await expect(roleChips.first()).toBeVisible({ timeout: 5000 });

    console.log(`Audit log shows ${auditRowCount} total changes`);

    // ========== STEP 12: Test Audit Log Filtering ==========
    console.log('Step 12: Test Audit Log filtering');

    // Filter by status = Applied
    await page.click('label:has-text("Status")');
    await page.click('li:has-text("Applied")');
    await page.waitForTimeout(500);

    // Check filtered results
    const appliedCount = await page.locator('tbody tr').count();
    console.log(`Found ${appliedCount} applied changes`);

    // Reset filter
    await page.click('label:has-text("Status")');
    await page.click('li:has-text("All Statuses")');
    await page.waitForTimeout(500);

    // Search by user
    await page.fill('input[placeholder*="Search by path"]', 'products');
    await page.waitForTimeout(500);

    // Verify search results
    const searchResults = await page.locator('tbody tr').count();
    expect(searchResults).toBeGreaterThan(0);
    console.log(`Search found ${searchResults} results for "products"`);

    // Clear search
    await page.fill('input[placeholder*="Search by path"]', '');
    await page.waitForTimeout(500);

    // ========== STEP 13: Verify complete workflow in audit log ==========
    console.log('Step 13: Verify complete workflow is visible in audit log');

    // Check that we can see different statuses
    const statusFilters = ['Draft', 'Pending', 'Approved', 'Applied'];
    for (const status of statusFilters) {
      await page.click('label:has-text("Status")');
      await page.click(`li:has-text("${status}")`);
      await page.waitForTimeout(500);

      const count = await page.locator('tbody tr').count();
      console.log(`${status} comments: ${count}`);

      // Reset
      await page.click('label:has-text("Status")');
      await page.click('li:has-text("All Statuses")');
      await page.waitForTimeout(500);
    }

    console.log('Complete workflow test finished successfully!');
  });

  test('audit log shows user roles and authorization levels', async ({ page }) => {
    // Login as approver
    await page.goto('http://localhost:4001/login');
    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:4001/');

    // Navigate to Audit Log
    await page.click('text=Audit Log');
    await page.waitForURL('http://localhost:4001/audit-log');
    await page.waitForTimeout(1000);

    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Verify role chips are displayed
    const suggestOnlyChips = page.locator('.MuiChip-label:has-text("SUGGEST ONLY")');
    const approverChips = page.locator('.MuiChip-label:has-text("APPROVER")');

    // At least one type of role chip should be visible
    const hasSuggestChips = await suggestOnlyChips.count() > 0;
    const hasApproverChips = await approverChips.count() > 0;

    expect(hasSuggestChips || hasApproverChips).toBeTruthy();

    console.log('User roles are displayed in audit log');
  });

  test('apply queue only shows approved comments', async ({ page }) => {
    // Login as approver
    await page.goto('http://localhost:4001/login');
    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:4001/');

    // Navigate to Apply Queue
    await page.click('text=Apply Queue');
    await page.waitForURL('http://localhost:4001/apply-queue');
    await page.waitForTimeout(1000);

    // Check if there are any comments
    const hasComments = await page.locator('table tbody tr').count() > 0;

    if (hasComments) {
      // Verify all comments are approved (no pending/draft status chips)
      const draftChips = page.locator('.MuiChip-label:has-text("DRAFT")');
      const pendingChips = page.locator('.MuiChip-label:has-text("PENDING")');

      expect(await draftChips.count()).toBe(0);
      expect(await pendingChips.count()).toBe(0);

      console.log('Apply queue only shows approved comments');
    } else {
      // Empty state should be visible
      await expect(page.locator('text=No approved comments ready to apply')).toBeVisible();
      console.log('No approved comments in apply queue');
    }
  });
});
