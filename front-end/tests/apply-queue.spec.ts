import { test, expect } from '@playwright/test';

test.describe('Apply Queue', () => {
  test.beforeEach(async ({ page }) => {
    // Login as approver user
    await page.goto('http://localhost:4001/login');
    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('button[type="submit"]');

    // Wait for login to complete
    await page.waitForURL('http://localhost:4001/');

    // Navigate to Apply Queue
    await page.click('text=Apply Queue');
    await page.waitForURL('http://localhost:4001/apply-queue');
  });

  test('should display apply queue page', async ({ page }) => {
    // Check page title
    await expect(page.locator('h4:has-text("Apply Queue")')).toBeVisible();

    // Check description
    await expect(page.locator('text=Apply approved metadata changes to Databricks')).toBeVisible();
  });

  test('should display approved comments table', async ({ page }) => {
    // Wait for table or empty state
    await page.waitForSelector('table, text=No approved comments ready to apply', { timeout: 10000 });

    // Check if there are approved comments or empty state
    const hasTable = await page.locator('table').isVisible().catch(() => false);
    const hasEmptyState = await page.locator('text=No approved comments ready to apply').isVisible().catch(() => false);

    expect(hasTable || hasEmptyState).toBeTruthy();
  });

  test('should show empty state when no approved comments', async ({ page }) => {
    // Check for empty state elements
    const emptyState = page.locator('text=No approved comments ready to apply');
    const hasEmptyState = await emptyState.isVisible().catch(() => false);

    if (hasEmptyState) {
      await expect(emptyState).toBeVisible();
      await expect(page.locator('text=Comments will appear here after')).toBeVisible();
    }
  });

  test('should display table headers when comments exist', async ({ page }) => {
    // Wait for table to potentially load
    await page.waitForTimeout(1000);

    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Check table headers
      await expect(page.locator('th:has-text("Entity")')).toBeVisible();
      await expect(page.locator('th:has-text("Type")')).toBeVisible();
      await expect(page.locator('th:has-text("Current Comment")')).toBeVisible();
      await expect(page.locator('th:has-text("Suggested Comment")')).toBeVisible();
      await expect(page.locator('th:has-text("Created By")')).toBeVisible();
      await expect(page.locator('th:has-text("Approved By")')).toBeVisible();
      await expect(page.locator('th:has-text("Actions")')).toBeVisible();
    }
  });

  test('should allow selecting individual comments with checkbox', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Check if there are any rows
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Click first checkbox
        await rows.first().locator('input[type="checkbox"]').click();

        // Verify checkbox is checked
        await expect(rows.first().locator('input[type="checkbox"]')).toBeChecked();

        // Verify batch apply button appears
        await expect(page.locator('button:has-text("Apply Selected")')).toBeVisible();
      }
    }
  });

  test('should allow selecting all comments', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Click select all checkbox in header
        await page.locator('thead input[type="checkbox"]').click();

        // Verify all checkboxes are checked
        const firstCheckbox = rows.first().locator('input[type="checkbox"]');
        await expect(firstCheckbox).toBeChecked();

        // Verify batch apply button shows correct count
        await expect(page.locator(`button:has-text("Apply Selected (${rowCount})")`)).toBeVisible();
      }
    }
  });

  test('should display apply button for each comment', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Check first row has Apply button
        await expect(rows.first().locator('button:has-text("Apply")')).toBeVisible();
      }
    }
  });

  test('should open confirmation dialog when clicking apply', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Click apply button on first row
        await rows.first().locator('button:has-text("Apply")').click();

        // Wait for dialog
        await page.waitForSelector('text=Apply Comment to Databricks');

        // Check dialog content
        await expect(page.locator('text=Apply Comment to Databricks')).toBeVisible();
        await expect(page.locator('text=This will update the metadata in Databricks')).toBeVisible();
        await expect(page.locator('text=Entity:')).toBeVisible();
        await expect(page.locator('text=Current Comment:')).toBeVisible();
        await expect(page.locator('text=New Comment:')).toBeVisible();

        // Check dialog buttons
        await expect(page.locator('button:has-text("Cancel")')).toBeVisible();
        await expect(page.locator('button:has-text("Apply to Databricks")')).toBeVisible();
      }
    }
  });

  test('should cancel apply dialog', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Click apply button
        await rows.first().locator('button:has-text("Apply")').click();

        // Wait for dialog
        await page.waitForSelector('text=Apply Comment to Databricks');

        // Click cancel
        await page.click('button:has-text("Cancel")');

        // Dialog should be closed
        await expect(page.locator('text=Apply Comment to Databricks')).not.toBeVisible();
      }
    }
  });

  test('should show pagination controls', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Check pagination controls
      await expect(page.locator('text=Rows per page')).toBeVisible();
    }
  });

  test('should display comment details in table', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Check that first row has entity path (monospace)
        const entityPath = rows.first().locator('td [style*="monospace"]');
        await expect(entityPath).toBeVisible();

        // Check that entity type chip is visible
        const typeChip = rows.first().locator('td .MuiChip-label');
        await expect(typeChip.first()).toBeVisible();
      }
    }
  });

  test('should be accessible only to approvers and admins', async ({ page }) => {
    // Already logged in as approver, so page should be accessible
    await expect(page.locator('h4:has-text("Apply Queue")')).toBeVisible();

    // Logout
    await page.click('[data-testid="user-profile"]');
    await page.click('text=Logout');

    // Login as suggest_only user
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:4001/');

    // Apply Queue menu item should not be visible
    await expect(page.locator('text=Apply Queue')).not.toBeVisible();
  });

  test('should show approved by information', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // Check that approved by column shows user info
        const approvedByCell = rows.first().locator('td').nth(6); // Approved By column
        await expect(approvedByCell).toBeVisible();
      }
    }
  });

  test('should unselect items when clicked again', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();

      if (rowCount > 0) {
        const firstCheckbox = rows.first().locator('input[type="checkbox"]');

        // Click to select
        await firstCheckbox.click();
        await expect(firstCheckbox).toBeChecked();

        // Click to unselect
        await firstCheckbox.click();
        await expect(firstCheckbox).not.toBeChecked();

        // Batch apply button should be hidden
        await expect(page.locator('button:has-text("Apply Selected")')).not.toBeVisible();
      }
    }
  });
});
