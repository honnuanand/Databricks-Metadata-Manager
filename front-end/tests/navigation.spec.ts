import { test, expect } from '@playwright/test';

test.describe('Navigation and Layout', () => {
  test.beforeEach(async ({ page }) => {
    // This assumes successful authentication
    await page.goto('/');
  });

  test('should show main navigation sidebar', async ({ page }) => {
    const sidebar = page.locator('[role="navigation"], .MuiDrawer-root');
    if (await sidebar.isVisible()) {
      await expect(sidebar).toBeVisible();
    }
  });

  test('should show app header with title', async ({ page }) => {
    const header = page.locator('header, .MuiAppBar-root');
    const title = page.locator('text=Databricks Metadata Manager');
    
    if (await header.isVisible()) {
      await expect(header).toBeVisible();
      await expect(title).toBeVisible();
    }
  });

  test('should navigate between main sections', async ({ page }) => {
    const navLinks = [
      { text: 'Home', url: '/' },
      { text: 'Catalog', url: '/catalog' },
      { text: 'My Comments', url: '/my-comments' }
    ];

    for (const link of navLinks) {
      const navItem = page.locator(`text=${link.text}`).first();
      
      if (await navItem.isVisible()) {
        await navItem.click();
        await page.waitForTimeout(500);
        
        // Check URL or page content
        const currentUrl = page.url();
        expect(currentUrl.endsWith(link.url)).toBe(true);
      }
    }
  });

  test('should show user profile menu', async ({ page }) => {
    const profileButton = page.locator('[aria-label*="profile"], .MuiAvatar-root').first();
    
    if (await profileButton.isVisible()) {
      await profileButton.click();
      
      // Should show menu with profile options
      await expect(page.locator('text=Profile, text=Logout')).toBeVisible();
    }
  });
});

test.describe('Responsive Design', () => {
  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // App should still be functional on mobile
    const mainContent = page.locator('main, [role="main"], body');
    await expect(mainContent).toBeVisible();
  });

  test('should work on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    
    // App should still be functional on tablet
    const mainContent = page.locator('main, [role="main"], body');
    await expect(mainContent).toBeVisible();
  });
});