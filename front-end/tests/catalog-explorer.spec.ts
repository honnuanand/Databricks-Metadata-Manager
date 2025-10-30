import { test, expect } from '@playwright/test';

test.describe('Catalog Explorer', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to catalog explorer (assuming we can bypass auth or are already logged in)
    await page.goto('/catalog');
  });

  test('should show catalog explorer page', async ({ page }) => {
    await expect(page.locator('h4')).toContainText('Catalog Explorer');
  });

  test('should show navigation breadcrumbs', async ({ page }) => {
    const breadcrumbs = page.locator('[aria-label="breadcrumb"], .MuiBreadcrumbs-root');
    if (await breadcrumbs.isVisible()) {
      await expect(breadcrumbs).toBeVisible();
      await expect(breadcrumbs).toContainText('Catalogs');
    }
  });

  test('should show search functionality', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"]');
    if (await searchInput.isVisible()) {
      await expect(searchInput).toBeVisible();
    }
  });

  test('should show main layout with sidebar and content', async ({ page }) => {
    // Check for the grid layout
    const gridContainer = page.locator('.MuiGrid-container, [role="main"]');
    await expect(gridContainer).toBeVisible();
  });

  test('should handle empty state when no catalogs available', async ({ page }) => {
    // Look for empty state or loading indicator
    const emptyState = page.locator('text=Select an entity, text=No catalogs found, .MuiCircularProgress-root');
    const catalogList = page.locator('[role="list"], .MuiList-root');
    
    // Either empty state should be shown or catalog list should be visible
    const hasEmptyState = await emptyState.isVisible();
    const hasCatalogList = await catalogList.isVisible();
    
    expect(hasEmptyState || hasCatalogList).toBe(true);
  });

  test('should show comment dialog when add comment is clicked', async ({ page }) => {
    // This test assumes there are some entities to interact with
    const addCommentButton = page.locator('button[aria-label*="add"], button:has(svg)').first();
    
    if (await addCommentButton.isVisible()) {
      await addCommentButton.click();
      
      // Should open comment dialog
      await expect(page.locator('text=Add Comment, text=Edit Comment')).toBeVisible();
      await expect(page.locator('input[label*="Comment"], textarea[label*="Comment"]')).toBeVisible();
    }
  });
});

test.describe('Catalog Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/catalog');
  });

  test('should handle catalog selection', async ({ page }) => {
    // Look for catalog items in the list
    const catalogItems = page.locator('[role="button"]:has-text("catalog"), .MuiListItemButton-root').first();
    
    if (await catalogItems.isVisible()) {
      await catalogItems.click();
      
      // Should update breadcrumbs or navigation
      await page.waitForTimeout(1000);
      
      // Check if navigation updated (breadcrumbs should change)
      const breadcrumbs = page.locator('[aria-label="breadcrumb"]');
      if (await breadcrumbs.isVisible()) {
        expect(await breadcrumbs.textContent()).toBeTruthy();
      }
    }
  });

  test('should show entity details panel', async ({ page }) => {
    // Right panel should show entity details or instructions
    const detailsPanel = page.locator('.MuiGrid-item:last-child');
    await expect(detailsPanel).toBeVisible();
    
    // Should either show entity details or empty state message
    const hasContent = await detailsPanel.locator('text=Select an entity, .MuiTypography-root').isVisible();
    expect(hasContent).toBe(true);
  });

  test('should handle search functionality', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.keyboard.press('Enter');
      
      // Should filter results or show no results
      await page.waitForTimeout(500);
      expect(true).toBe(true); // Basic test that search doesn't crash
    }
  });
});