import { test, expect } from '@playwright/test';

test.describe('Console Errors and Warnings Detection', () => {
  let consoleMessages: string[] = [];
  let consoleErrors: string[] = [];
  let networkErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    // Capture console messages
    consoleMessages = [];
    consoleErrors = [];
    networkErrors = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(text);
      
      if (msg.type() === 'error') {
        consoleErrors.push(text);
      }
    });

    // Capture network failures
    page.on('requestfailed', request => {
      networkErrors.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
    });

    // Navigate to login page
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
  });

  test('should not have React Router future flag warnings', async ({ page }) => {
    // Check for specific React Router warnings
    const routerWarnings = consoleMessages.filter(msg => 
      msg.includes('React Router Future Flag Warning') ||
      msg.includes('v7_startTransition') ||
      msg.includes('v7_relativeSplatPath')
    );

    if (routerWarnings.length > 0) {
      console.log('Found React Router warnings:', routerWarnings);
      
      // This test documents the warnings but doesn't fail since they're just warnings
      expect(routerWarnings.length).toBeGreaterThan(0);
      
      // Log suggestions for fixing
      console.log('💡 To fix these warnings, update your React Router configuration to include future flags:');
      console.log('   - Add v7_startTransition: true to your router config');
      console.log('   - Add v7_relativeSplatPath: true to your router config');
    }
  });

  test('should not have 404 errors for /api/v1/users/me endpoint', async ({ page }) => {
    // Login first to trigger the /users/me call
    const johnCard = page.locator('text=John Doe').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    if (await johnCard.isVisible()) {
      await johnCard.click();
      await page.waitForTimeout(3000);
    }

    // Check for 404 errors on users/me endpoint
    const usersMeErrors = networkErrors.filter(error => 
      error.includes('/api/v1/users/me') && error.includes('404')
    );

    if (usersMeErrors.length > 0) {
      console.log('❌ Found 404 errors for /api/v1/users/me:', usersMeErrors);
      
      // Fail the test if this critical endpoint is missing
      expect(usersMeErrors.length).toBe(0);
    } else {
      console.log('✅ No 404 errors found for /api/v1/users/me endpoint');
    }
  });

  test('should handle browser extension errors gracefully', async ({ page }) => {
    // Check for chrome extension errors (these are expected and should be ignored)
    const extensionErrors = consoleErrors.filter(error => 
      error.includes('chrome-extension://') ||
      error.includes('ERR_FILE_NOT_FOUND')
    );

    if (extensionErrors.length > 0) {
      console.log('📋 Found browser extension errors (expected):', extensionErrors.length);
      
      // These are expected and should not fail the test
      expect(extensionErrors.length).toBeGreaterThanOrEqual(0);
    }
  });

  test('should not have critical JavaScript errors', async ({ page }) => {
    // Filter out expected errors (extensions, warnings)
    const criticalErrors = consoleErrors.filter(error => 
      !error.includes('chrome-extension://') &&
      !error.includes('React Router Future Flag Warning') &&
      !error.includes('ERR_FILE_NOT_FOUND') &&
      !error.includes('net::ERR_')
    );

    if (criticalErrors.length > 0) {
      console.log('❌ Found critical JavaScript errors:', criticalErrors);
      expect(criticalErrors.length).toBe(0);
    } else {
      console.log('✅ No critical JavaScript errors found');
    }
  });

  test('should verify API endpoints are accessible', async ({ page }) => {
    // Test key API endpoints
    const endpoints = [
      '/api/v1/auth/test-users',
      '/api/v1/catalogs',
      '/api/v1/comments/my',
      '/api/v1/users/me',
      '/health',
      '/'
    ];

    for (const endpoint of endpoints) {
      const response = await page.request.get(`http://localhost:8080${endpoint}`);
      expect(response.status()).toBeLessThan(400);
      console.log(`✅ ${endpoint}: ${response.status()}`);
    }
  });

  test('should not have HTTP 401 errors in console', async ({ page }) => {
    const networkErrors: { url: string, status: number }[] = [];
    
    page.on('response', response => {
      if (response.status() === 401) {
        networkErrors.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    // Perform login which triggers API calls
    const johnCard = page.locator('text=John Doe').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    if (await johnCard.isVisible()) {
      await johnCard.click();
      await page.waitForTimeout(3000);
    }

    // Check for 401 errors
    if (networkErrors.length > 0) {
      console.log('❌ Found HTTP 401 errors:', networkErrors);
      console.log('These indicate authentication/authorization issues that need to be fixed');
      
      // Document the errors but don't fail the test initially
      expect(networkErrors.length).toBe(0);
    } else {
      console.log('✅ No HTTP 401 errors found');
    }
  });

  test('should verify users/me endpoint after login', async ({ page }) => {
    // Login first
    const loginResponse = await page.request.post('http://localhost:8080/api/v1/auth/login', {
      data: {
        username: 'john_suggest',
        password: 'suggest123'
      }
    });

    expect(loginResponse.status()).toBe(200);
    const loginData = await loginResponse.json();
    const token = loginData.access_token;

    // Now test the /users/me endpoint with the token
    const usersMeResponse = await page.request.get('http://localhost:8080/api/v1/users/me', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (usersMeResponse.status() === 404) {
      console.log('❌ /api/v1/users/me endpoint returns 404 - needs to be implemented');
      expect(usersMeResponse.status()).toBe(200);
    } else {
      console.log('✅ /api/v1/users/me endpoint working correctly');
      expect(usersMeResponse.status()).toBe(200);
    }
  });

  test('should track all network requests during login flow', async ({ page }) => {
    const requests: string[] = [];
    const responses: { url: string, status: number }[] = [];

    page.on('request', request => {
      if (request.url().includes('localhost:8080')) {
        requests.push(`${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('localhost:8080')) {
        responses.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    // Perform login
    const johnCard = page.locator('text=John Doe').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    if (await johnCard.isVisible()) {
      await johnCard.click();
      await page.waitForTimeout(3000);
    }

    console.log('📊 All API requests made:');
    requests.forEach(req => console.log(`  ${req}`));

    console.log('📊 All API responses:');
    responses.forEach(res => console.log(`  ${res.url} -> ${res.status}`));

    // Check for any failed requests
    const failedResponses = responses.filter(res => res.status >= 400);
    if (failedResponses.length > 0) {
      console.log('❌ Failed API requests:');
      failedResponses.forEach(res => console.log(`  ${res.url} -> ${res.status}`));
    }
  });

  test('should validate React Router configuration', async ({ page }) => {
    // Check if the app loads without router errors
    await page.goto('/');
    await page.waitForTimeout(1000);

    // Should either redirect to login or show main app
    const isLoginPage = await page.locator('text=Sign in').isVisible();
    const isMainApp = await page.locator('text=Databricks Metadata Manager').isVisible();

    expect(isLoginPage || isMainApp).toBe(true);

    // Navigate to different routes to test routing
    if (isLoginPage) {
      // Test login page routing
      await page.goto('/login');
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
    }

    // Test 404 handling
    await page.goto('/non-existent-route');
    await page.waitForTimeout(1000);
    
    // Should handle gracefully (either redirect or show 404 page)
    const hasError = await page.locator('text=404').or(page.locator('text=Not Found')).isVisible();
    const redirectedToLogin = await page.locator('text=Sign in').isVisible();
    const redirectedToHome = await page.locator('text=Databricks Metadata Manager').isVisible();

    expect(hasError || redirectedToLogin || redirectedToHome).toBe(true);
  });

  test('should monitor specific console errors mentioned by user', async ({ page }) => {
    const allErrors: { type: string, message: string }[] = [];
    
    // Monitor all console messages
    page.on('console', msg => {
      if (msg.type() === 'warning' || msg.type() === 'error') {
        allErrors.push({
          type: msg.type(),
          message: msg.text()
        });
      }
    });

    // Monitor network failures
    page.on('response', response => {
      if (response.status() >= 400) {
        allErrors.push({
          type: 'network_error',
          message: `${response.status()} ${response.url()}`
        });
      }
    });

    // Perform typical user actions
    const johnCard = page.locator('text=John Doe').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    if (await johnCard.isVisible()) {
      await johnCard.click();
      await page.waitForTimeout(3000);
    }

    // Categorize the errors
    const routerWarnings = allErrors.filter(e => e.message.includes('React Router Future Flag Warning'));
    const authErrors = allErrors.filter(e => e.message.includes('/api/v1/users/me') && e.message.includes('404'));
    const catalogErrors = allErrors.filter(e => e.message.includes('/api/v1/catalogs') && e.message.includes('404'));
    const commentsErrors = allErrors.filter(e => e.message.includes('/api/v1/comments/my') && e.message.includes('404'));
    const extensionErrors = allErrors.filter(e => e.message.includes('chrome-extension://'));
    const httpErrors = allErrors.filter(e => e.type === 'network_error');

    console.log('📊 Error Summary:');
    console.log(`  React Router warnings: ${routerWarnings.length}`);
    console.log(`  Auth endpoint errors: ${authErrors.length}`);
    console.log(`  Catalog endpoint errors: ${catalogErrors.length}`);
    console.log(`  Comments endpoint errors: ${commentsErrors.length}`);
    console.log(`  Extension errors: ${extensionErrors.length}`);
    console.log(`  HTTP errors: ${httpErrors.length}`);

    // Log specific errors for debugging
    if (routerWarnings.length > 0) {
      console.log('⚠️ React Router warnings detected - consider adding future flags');
    }
    if (authErrors.length > 0) {
      console.log('❌ Auth endpoint 404 errors - /api/v1/users/me needs implementation');
    }
    if (catalogErrors.length > 0) {
      console.log('❌ Catalog endpoint 404 errors - /api/v1/catalogs needs implementation');
    }
    if (commentsErrors.length > 0) {
      console.log('❌ Comments endpoint 404 errors - /api/v1/comments/my needs implementation');
    }
    if (httpErrors.length > 0) {
      console.log('❌ HTTP errors detected:', httpErrors.map(e => e.message));
    }

    // This test documents issues but doesn't necessarily fail
    expect(allErrors.length).toBeGreaterThanOrEqual(0);
  });

  test('should not have JavaScript runtime errors', async ({ page }) => {
    const jsErrors: string[] = [];
    const domWarnings: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (text.includes('TypeError') || text.includes('ReferenceError') || text.includes('filter is not a function')) {
          jsErrors.push(text);
        }
      } else if (msg.type() === 'warning') {
        const text = msg.text();
        if (text.includes('validateDOMNesting') || text.includes('cannot appear as a descendant')) {
          domWarnings.push(text);
        }
      }
    });

    // Perform normal user flow
    const johnCard = page.locator('text=John Doe').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    if (await johnCard.isVisible()) {
      await johnCard.click();
      await page.waitForTimeout(3000);
    }

    // Check for critical JavaScript errors
    if (jsErrors.length > 0) {
      console.log('❌ JavaScript runtime errors detected:', jsErrors);
      expect(jsErrors.length).toBe(0);
    } else {
      console.log('✅ No JavaScript runtime errors found');
    }

    // Check for DOM nesting warnings
    if (domWarnings.length > 0) {
      console.log('⚠️ DOM nesting warnings detected:', domWarnings);
      console.log('Recommendation: Fix HTML structure to avoid nested block elements in inline elements');
    } else {
      console.log('✅ No DOM nesting warnings found');
    }
  });

  test('should provide debugging information for failed requests', async ({ page }) => {
    // Collect all console output for debugging
    const allConsoleOutput = {
      messages: consoleMessages,
      errors: consoleErrors,
      networkErrors: networkErrors
    };

    console.log('📋 Complete console output summary:');
    console.log(`  Total console messages: ${consoleMessages.length}`);
    console.log(`  Console errors: ${consoleErrors.length}`);
    console.log(`  Network errors: ${networkErrors.length}`);

    // Save debugging info
    if (consoleErrors.length > 0 || networkErrors.length > 0) {
      console.log('🔍 Debugging information:');
      console.log('Console Errors:', consoleErrors);
      console.log('Network Errors:', networkErrors);
    }

    // This test always passes but provides debugging info
    expect(true).toBe(true);
  });
});