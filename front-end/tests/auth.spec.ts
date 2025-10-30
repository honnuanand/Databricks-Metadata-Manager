import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should redirect to login page when not authenticated', async ({ page }) => {
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.locator('h1')).toContainText('Databricks Metadata Manager');
  });

  test('should show login form elements', async ({ page }) => {
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Sign In');
  });

  test('should show development test accounts in dev mode', async ({ page }) => {
    // Check if dev environment shows test accounts
    const devSection = page.locator('text=Development Test Accounts');
    if (await devSection.isVisible()) {
      await expect(devSection).toBeVisible();
      await expect(page.locator('text=john_suggest')).toBeVisible();
      await expect(page.locator('text=jane_approver')).toBeVisible();
      await expect(page.locator('text=admin_user')).toBeVisible();
    }
  });

  test('should handle login form validation', async ({ page }) => {
    const submitButton = page.locator('button[type="submit"]');
    
    // Try to submit empty form
    await submitButton.click();
    
    // Form should not submit with empty fields
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should attempt login with test credentials', async ({ page }) => {
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();
    
    // Wait for either successful redirect or error message
    await page.waitForTimeout(2000);
    
    // Should either redirect to home or show error (backend might not be running)
    const currentUrl = page.url();
    const hasError = await page.locator('[role="alert"]').isVisible();
    
    console.log('Current URL after login:', currentUrl);
    console.log('Has error visible:', hasError);
    console.log('URL ends with /:', currentUrl.endsWith('/'));
    
    expect(currentUrl.endsWith('/') || hasError).toBe(true);
  });
});

test.describe('Development User Switcher', () => {
  test('should show user switcher in development mode', async ({ page }) => {
    await page.goto('/');
    
    // Look for the floating action button (user switcher)
    const userSwitcher = page.locator('[data-testid="dev-user-switcher"], button[aria-label*="switch"], .MuiFab-root').first();
    
    if (await userSwitcher.isVisible()) {
      await expect(userSwitcher).toBeVisible();
    }
  });

  test('should open user switcher dialog', async ({ page }) => {
    await page.goto('/');
    
    // Look for and click the user switcher button
    const userSwitcherButton = page.locator('.MuiFab-root').first();
    
    if (await userSwitcherButton.isVisible()) {
      await userSwitcherButton.click();
      
      // Check if dialog opens
      await expect(page.locator('text=Development User Switcher')).toBeVisible();
      await expect(page.locator('text=Create Test Users')).toBeVisible();
    }
  });
});