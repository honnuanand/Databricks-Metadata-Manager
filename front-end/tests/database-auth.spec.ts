import { test, expect } from '@playwright/test';

/**
 * Database Authentication Tests
 * Tests login flow with PostgreSQL/Neon database authentication
 * against the deployed Databricks Apps instance
 *
 * Note: Databricks Apps enforces SSO authentication as a security layer.
 * These tests work with the API endpoints directly which bypass the browser-based SSO.
 * For browser tests, users must first authenticate to Databricks workspace.
 */

const APP_URL = 'https://metadata-manager-2409307273843806.aws.databricksapps.com';

// Skip browser-based tests in CI since they require Databricks SSO login
const skipBrowserTests = true;

// Test users seeded in the database
const testUsers = {
  admin: {
    email: 'admin@example.com',
    password: 'admin123',
    role: 'admin',
    expectedPermissions: ['can_manage_users', 'can_view_audit_logs']
  },
  approver: {
    email: 'approver@example.com',
    password: 'approver123',
    role: 'approver',
    expectedPermissions: ['can_approve_suggestions', 'can_apply_suggestions']
  },
  user: {
    email: 'user@example.com',
    password: 'user123',
    role: 'suggest_only',
    expectedPermissions: ['can_create_suggestions']
  }
};

test.describe('Database Authentication - Production (Browser)', () => {
  test.skip(skipBrowserTests, 'Browser tests require Databricks SSO authentication');

  test.beforeEach(async ({ page }) => {
    // Clear any existing session
    await page.context().clearCookies();
    await page.goto(APP_URL);
  });

  test('should load the application and show login page', async ({ page }) => {
    await expect(page).toHaveURL(new RegExp(`${APP_URL}/login`));
    await expect(page.locator('h1, h2, h3')).toContainText(/metadata|login/i);
  });

  test('should have all login form elements', async ({ page }) => {
    await expect(page.locator('input[name="username"], input[type="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"], input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should reject invalid credentials', async ({ page }) => {
    await page.fill('input[name="username"], input[type="email"]', 'invalid@example.com');
    await page.fill('input[name="password"], input[type="password"]', 'wrongpassword');
    await page.locator('button[type="submit"]').click();

    // Should show error message or stay on login page
    await page.waitForTimeout(2000);
    const hasError = await page.locator('[role="alert"], .error, .MuiAlert-root').isVisible().catch(() => false);
    const stillOnLogin = page.url().includes('/login');

    expect(hasError || stillOnLogin).toBe(true);
  });

  test('should successfully login as admin user', async ({ page }) => {
    // Fill in admin credentials
    await page.fill('input[name="username"], input[type="email"]', testUsers.admin.email);
    await page.fill('input[name="password"], input[type="password"]', testUsers.admin.password);

    // Submit login form
    await page.locator('button[type="submit"]').click();

    // Wait for navigation or response
    await page.waitForTimeout(3000);

    // Should redirect to home page after successful login
    const currentUrl = page.url();
    const redirectedToHome = currentUrl === APP_URL + '/' || currentUrl === APP_URL;
    const hasError = await page.locator('[role="alert"].error, .MuiAlert-error').isVisible().catch(() => false);

    console.log('Login attempt result:');
    console.log('  Current URL:', currentUrl);
    console.log('  Has error:', hasError);
    console.log('  Redirected to home:', redirectedToHome);

    // Check for successful redirect
    expect(redirectedToHome && !hasError).toBe(true);
  });

  test('should successfully login as approver user', async ({ page }) => {
    await page.fill('input[name="username"], input[type="email"]', testUsers.approver.email);
    await page.fill('input[name="password"], input[type="password"]', testUsers.approver.password);
    await page.locator('button[type="submit"]').click();

    await page.waitForTimeout(3000);

    const redirectedToHome = page.url() === APP_URL + '/' || page.url() === APP_URL;
    const hasError = await page.locator('[role="alert"].error').isVisible().catch(() => false);

    expect(redirectedToHome && !hasError).toBe(true);
  });

  test('should successfully login as regular user', async ({ page }) => {
    await page.fill('input[name="username"], input[type="email"]', testUsers.user.email);
    await page.fill('input[name="password"], input[type="password"]', testUsers.user.password);
    await page.locator('button[type="submit"]').click();

    await page.waitForTimeout(3000);

    const redirectedToHome = page.url() === APP_URL + '/' || page.url() === APP_URL;
    const hasError = await page.locator('[role="alert"].error').isVisible().catch(() => false);

    expect(redirectedToHome && !hasError).toBe(true);
  });

  test('should persist session after login', async ({ page }) => {
    // Login as admin
    await page.fill('input[name="username"], input[type="email"]', testUsers.admin.email);
    await page.fill('input[name="password"], input[type="password"]', testUsers.admin.password);
    await page.locator('button[type="submit"]').click();

    await page.waitForTimeout(3000);

    // Reload the page
    await page.reload();
    await page.waitForTimeout(2000);

    // Should still be logged in (not redirected to login)
    const stillLoggedIn = !page.url().includes('/login');
    expect(stillLoggedIn).toBe(true);
  });
});

test.describe('Database Authentication - API Endpoints', () => {
  test('should return 401 for /api/v1/auth/me without token', async ({ request }) => {
    const response = await request.get(`${APP_URL}/api/v1/auth/me`);
    expect(response.status()).toBe(401);
  });

  test('should successfully authenticate via API', async ({ request }) => {
    const response = await request.post(`${APP_URL}/api/v1/auth/login`, {
      data: {
        username: testUsers.admin.email,
        password: testUsers.admin.password
      }
    });

    console.log('API Login response status:', response.status());

    if (response.status() === 200) {
      const data = await response.json();
      console.log('API Login response:', JSON.stringify(data, null, 2));

      expect(data).toHaveProperty('access_token');
      expect(data).toHaveProperty('refresh_token');
      expect(data).toHaveProperty('user');
      expect(data.user.email).toBe(testUsers.admin.email);
      expect(data.user.role).toBe(testUsers.admin.role);
    } else {
      const text = await response.text();
      console.log('API Login error response:', text);
      throw new Error(`Login failed with status ${response.status()}: ${text}`);
    }
  });

  test('should access /api/v1/auth/me with valid token', async ({ request }) => {
    // First, login to get token
    const loginResponse = await request.post(`${APP_URL}/api/v1/auth/login`, {
      data: {
        username: testUsers.admin.email,
        password: testUsers.admin.password
      }
    });

    expect(loginResponse.status()).toBe(200);
    const loginData = await loginResponse.json();
    const accessToken = loginData.access_token;

    // Then, use token to access /me endpoint
    const meResponse = await request.get(`${APP_URL}/api/v1/auth/me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    expect(meResponse.status()).toBe(200);
    const meData = await meResponse.json();
    expect(meData.user.email).toBe(testUsers.admin.email);
  });
});

test.describe('Health Check', () => {
  test('should return healthy status with database connectivity', async ({ request }) => {
    const response = await request.get(`${APP_URL}/health`);
    expect(response.status()).toBe(200);

    const data = await response.json();
    console.log('Health check response:', JSON.stringify(data, null, 2));

    expect(data.status).toBe('healthy');
    expect(data.services.database).toBe('connected');
    expect(data.database_user_count).toBeGreaterThan(0);
  });
});
