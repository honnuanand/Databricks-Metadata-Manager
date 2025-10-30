import { test, expect } from '@playwright/test';

/**
 * Local Development Login Tests
 * Tests the complete login flow against local services:
 * - Backend: http://localhost:8080
 * - Frontend: http://localhost:4001
 */

const LOCAL_URL = 'http://localhost:4001';

// Test users in Neon database
const testUsers = {
  admin: {
    email: 'admin@example.com',
    password: 'admin123',
    role: 'admin',
    expectedName: 'Admin User'
  },
  approver: {
    email: 'approver@example.com',
    password: 'approver123',
    role: 'approver',
    expectedName: 'Approver User'
  },
  user: {
    email: 'user@example.com',
    password: 'user123',
    role: 'suggest_only',
    expectedName: 'Test User'
  }
};

test.describe('Local Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing session
    await page.context().clearCookies();
    await page.goto(LOCAL_URL);
  });

  test('should load the login page', async ({ page }) => {
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.locator('h4, h5')).toContainText(/Databricks Metadata Manager/i);
  });

  test('should show quick login buttons for test users', async ({ page }) => {
    // Should show development test accounts section
    await expect(page.locator('text=Development Test Accounts')).toBeVisible();

    // Should show all three user types
    await expect(page.locator('text=Test User')).toBeVisible();
    await expect(page.locator('text=Approver User')).toBeVisible();
    await expect(page.locator('text=Admin User')).toBeVisible();
  });

  test('should successfully login as admin using form', async ({ page }) => {
    // Fill in credentials manually
    await page.fill('input[name="username"]', testUsers.admin.email);
    await page.fill('input[name="password"]', testUsers.admin.password);

    // Click sign in button
    await page.click('button:has-text("Sign In")');

    // Wait for navigation
    await page.waitForURL(/.*\/$/, { timeout: 5000 });

    // Should be on home page
    expect(page.url()).toBe(LOCAL_URL + '/');

    // Should see welcome message or user info
    await expect(page.locator('text=Catalog Explorer, text=Metadata Manager')).toBeVisible({ timeout: 10000 });
  });

  test('should successfully login as admin using quick login button', async ({ page }) => {
    // Click the admin quick login button
    await page.click('button:has-text("Quick Login"):near(:text("Admin User"))');

    // Wait for navigation
    await page.waitForURL(/.*\/$/, { timeout: 5000 });

    // Should be on home page
    expect(page.url()).toBe(LOCAL_URL + '/');
  });

  test('should successfully login as approver', async ({ page }) => {
    await page.fill('input[name="username"]', testUsers.approver.email);
    await page.fill('input[name="password"]', testUsers.approver.password);
    await page.click('button:has-text("Sign In")');

    await page.waitForURL(/.*\/$/, { timeout: 5000 });
    expect(page.url()).toBe(LOCAL_URL + '/');
  });

  test('should successfully login as regular user', async ({ page }) => {
    await page.fill('input[name="username"]', testUsers.user.email);
    await page.fill('input[name="password"]', testUsers.user.password);
    await page.click('button:has-text("Sign In")');

    await page.waitForURL(/.*\/$/, { timeout: 5000 });
    expect(page.url()).toBe(LOCAL_URL + '/');
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.fill('input[name="username"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button:has-text("Sign In")');

    // Should show error message
    await expect(page.locator('[role="alert"], .MuiAlert-root')).toBeVisible({ timeout: 3000 });

    // Should stay on login page
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should persist session after page reload', async ({ page }) => {
    // Login first
    await page.fill('input[name="username"]', testUsers.admin.email);
    await page.fill('input[name="password"]', testUsers.admin.password);
    await page.click('button:has-text("Sign In")');
    await page.waitForURL(/.*\/$/, { timeout: 5000 });

    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should still be logged in (not redirected to login)
    expect(page.url()).toBe(LOCAL_URL + '/');
  });
});

test.describe('Local Login - API Integration', () => {
  test('backend health check should work', async ({ request }) => {
    const response = await request.get('http://localhost:8080/health');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.services.database).toBe('connected');
  });

  test('should authenticate via API endpoint', async ({ request }) => {
    const response = await request.post('http://localhost:8080/api/v1/auth/login', {
      data: {
        username: testUsers.admin.email,
        password: testUsers.admin.password
      }
    });

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('access_token');
    expect(data).toHaveProperty('user');
    expect(data.user.email).toBe(testUsers.admin.email);
    expect(data.user.role).toBe(testUsers.admin.role);
  });

  test('should access protected endpoint with token', async ({ request }) => {
    // First login
    const loginResponse = await request.post('http://localhost:8080/api/v1/auth/login', {
      data: {
        username: testUsers.admin.email,
        password: testUsers.admin.password
      }
    });

    const loginData = await loginResponse.json();
    const token = loginData.access_token;

    // Then access protected endpoint
    const meResponse = await request.get('http://localhost:8080/api/v1/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    expect(meResponse.status()).toBe(200);

    const meData = await meResponse.json();
    expect(meData.user.email).toBe(testUsers.admin.email);
  });
});
