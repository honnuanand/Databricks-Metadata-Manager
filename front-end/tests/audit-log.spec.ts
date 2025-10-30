import { test, expect } from '@playwright/test';

test.describe('Audit Log', () => {
  test.beforeEach(async ({ page }) => {
    // Login as approver user
    await page.goto('http://localhost:4001/login');
    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('button[type="submit"]');

    // Wait for login to complete
    await page.waitForURL('http://localhost:4001/');

    // Navigate to Audit Log
    await page.click('text=Audit Log');
    await page.waitForURL('http://localhost:4001/audit-log');
  });

  test('should display audit log page with statistics', async ({ page }) => {
    // Check page title
    await expect(page.locator('h4:has-text("Audit Log")')).toBeVisible();

    // Check statistics cards are visible (these appear in the stats cards, not just in the table)
    await expect(page.locator('[class*="MuiCardContent"] >> text=Total Changes').first()).toBeVisible();
    await expect(page.locator('[class*="MuiCardContent"] >> text=Draft').first()).toBeVisible();
    await expect(page.locator('[class*="MuiCardContent"] >> text=Pending').first()).toBeVisible();
    await expect(page.locator('[class*="MuiCardContent"] >> text=Approved').first()).toBeVisible();
    await expect(page.locator('[class*="MuiCardContent"] >> text=Rejected').first()).toBeVisible();
    await expect(page.locator('[class*="MuiCardContent"] >> text=Applied').first()).toBeVisible();
  });

  test('should display comments table with data', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table');

    // Check table headers
    await expect(page.locator('th:has-text("Status")')).toBeVisible();
    await expect(page.locator('th:has-text("Entity")')).toBeVisible();
    await expect(page.locator('th:has-text("Type")')).toBeVisible();
    await expect(page.locator('th:has-text("Suggested Comment")')).toBeVisible();
    await expect(page.locator('th:has-text("Created By")')).toBeVisible();
    await expect(page.locator('th:has-text("Created At")')).toBeVisible();

    // Check that at least one row exists
    const rows = page.locator('tbody tr');
    await expect(rows).toHaveCount(5); // We have 5 test comments
  });

  test('should display user roles in the audit log', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Check that role chips are visible for users
    // Looking for the role chips (SUGGEST ONLY, APPROVER, etc.)
    const roleChips = page.locator('[class*="MuiChip"]').filter({ hasText: /SUGGEST ONLY|APPROVER|ADMIN/ });
    await expect(roleChips.first()).toBeVisible({ timeout: 10000 });
  });

  test('should filter by status', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Click status filter dropdown
    await page.click('label:has-text("Status")');
    await page.click('text=Approved');

    // Wait for filtering to apply
    await page.waitForTimeout(500);

    // Check that all visible rows have 'APPROVED' status
    const statusChips = page.locator('td .MuiChip-label:has-text("APPROVED")');
    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      await expect(statusChips.first()).toBeVisible();
    }
  });

  test('should filter by entity type', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Click entity type filter dropdown
    await page.click('label:has-text("Entity Type")');
    await page.click('li:has-text("Column")');

    // Wait for filtering to apply
    await page.waitForTimeout(500);

    // Check that filtered results are shown
    const typeChips = page.locator('td .MuiChip-label:has-text("column")');
    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      await expect(typeChips.first()).toBeVisible();
    }
  });

  test('should search by entity path', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Type in search box
    await page.fill('input[placeholder*="Search by path"]', 'metadata_test');

    // Wait for filtering to apply
    await page.waitForTimeout(500);

    // Check that results contain the search term
    const cells = page.locator('td [style*="monospace"]:has-text("metadata_test")');
    await expect(cells.first()).toBeVisible();
  });

  test('should search by user', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Type in user filter box
    await page.fill('input[placeholder*="Filter by user"]', 'john');

    // Wait for filtering to apply
    await page.waitForTimeout(500);

    // Check that results contain the user
    const userCells = page.locator('td:has-text("john")');
    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      await expect(userCells.first()).toBeVisible();
    }
  });

  test('should display pagination controls', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table');

    // Check pagination controls
    await expect(page.locator('text=Rows per page')).toBeVisible();

    // Check pagination text (e.g., "1–5 of 5")
    const paginationInfo = page.locator('[class*="MuiTablePagination-displayedRows"]');
    await expect(paginationInfo).toBeVisible();
  });

  test('should change rows per page', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table');

    // Click rows per page dropdown
    await page.click('div[role="button"]:has-text("25")');
    await page.click('li:has-text("10")');

    // Wait for update
    await page.waitForTimeout(500);

    // Verify it changed
    await expect(page.locator('div[role="button"]:has-text("10")')).toBeVisible();
  });

  test('should reset filters when clearing search', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    const initialRowCount = await page.locator('tbody tr').count();

    // Apply a search filter
    await page.fill('input[placeholder*="Search by path"]', 'nonexistent');
    await page.waitForTimeout(500);

    // Should show no results or fewer results
    const filteredRowCount = await page.locator('tbody tr').count();
    expect(filteredRowCount).toBeLessThanOrEqual(initialRowCount);

    // Clear the search
    await page.fill('input[placeholder*="Search by path"]', '');
    await page.waitForTimeout(500);

    // Should show original results
    const finalRowCount = await page.locator('tbody tr').count();
    expect(finalRowCount).toBe(initialRowCount);
  });

  test('should show approved by information with role', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table tbody tr');

    // Filter for approved comments
    await page.click('label:has-text("Status")');
    await page.click('text=Approved');
    await page.waitForTimeout(500);

    // Check if approved by information is shown
    const approvedByText = page.locator('text=Approved by:');
    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      await expect(approvedByText.first()).toBeVisible();
    }
  });

  test('should be accessible only to approvers and admins', async ({ page }) => {
    // Already logged in as approver, so page should be accessible
    await expect(page.locator('h4:has-text("Audit Log")')).toBeVisible();

    // Logout
    await page.click('[data-testid="user-profile"]');
    await page.click('text=Logout');

    // Login as suggest_only user
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:4001/');

    // Audit Log menu item should not be visible
    await expect(page.locator('text=Audit Log')).not.toBeVisible();
  });
});
