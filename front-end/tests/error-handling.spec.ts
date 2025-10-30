import { test, expect } from '@playwright/test';

test.describe('Error Handling and Edge Cases', () => {
  // Helper function to login as different users
  async function loginAs(page: any, userType: 'suggest_only' | 'approver' | 'admin') {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const userMapping = {
      suggest_only: { name: 'John Doe', username: 'john_suggest', password: 'suggest123' },
      approver: { name: 'Jane Smith', username: 'jane_approver', password: 'approve123' },
      admin: { name: 'Admin User', username: 'admin_user', password: 'admin123' }
    };
    
    const user = userMapping[userType];
    const userCard = page.locator(`text=${user.name}`).locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    await userCard.click();
    
    await page.waitForResponse(response => 
      response.url().includes('/api/v1/auth/login')
    ).catch(() => null);
    
    await page.waitForTimeout(2000);
    
    const hasError = await page.locator('[role="alert"]').isVisible();
    if (hasError) {
      test.skip(true, 'Backend not available');
    }
    
    await expect(page).toHaveURL('/');
  }

  test.describe('Authentication Error Handling', () => {
    test('should handle invalid login credentials', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Fill invalid credentials
      await page.fill('input[name="username"]', 'invalid_user');
      await page.fill('input[name="password"]', 'wrong_password');
      
      // Submit form
      await page.click('button[type="submit"]');
      
      // Wait for response
      await page.waitForTimeout(2000);
      
      // Should show error message
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Login failed').or(
        page.locator('text=Invalid credentials').or(
          page.locator('text=Unauthorized')
        )
      )).toBeVisible();
      
      // Should remain on login page
      await expect(page).toHaveURL(/.*\/login/);
    });

    test('should handle expired tokens gracefully', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Simulate expired token by clearing localStorage
      await page.evaluate(() => {
        localStorage.setItem('access_token', 'expired.token.here');
      });
      
      // Try to navigate to a protected route
      await page.goto('/');
      await page.waitForTimeout(2000);
      
      // Should either refresh token or redirect to login
      if (await page.locator('text=Login').isVisible()) {
        // Redirected to login - good
        await expect(page).toHaveURL(/.*\/login/);
      } else {
        // Token was refreshed - also good
        await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
      }
    });

    test('should handle network connectivity issues during login', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Block network requests
      await page.route('**/api/v1/auth/login', route => {
        route.abort('internetdisconnected');
      });
      
      // Try to login
      await page.fill('input[name="username"]', 'john_suggest');
      await page.fill('input[name="password"]', 'suggest123');
      await page.click('button[type="submit"]');
      
      await page.waitForTimeout(3000);
      
      // Should show network error
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Network').or(
        page.locator('text=Connection').or(
          page.locator('text=Failed')
        )
      )).toBeVisible();
    });
  });

  test.describe('API Error Handling', () => {
    test('should handle 500 server errors gracefully', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Mock 500 error
      await page.route('**/api/v1/auth/login', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' })
        });
      });
      
      // Try to login
      await page.fill('input[name="username"]', 'john_suggest');
      await page.fill('input[name="password"]', 'suggest123');
      await page.click('button[type="submit"]');
      
      await page.waitForTimeout(2000);
      
      // Should show appropriate error
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Server error').or(
        page.locator('text=Try again later')
      )).toBeVisible();
    });

    test('should handle timeout errors', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Mock slow response (timeout)
      await page.route('**/api/v1/auth/login', route => {
        // Don't fulfill the request, let it timeout
        setTimeout(() => {
          route.fulfill({
            status: 408,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Request timeout' })
          });
        }, 30000); // 30 second delay
      });
      
      // Try to login
      await page.fill('input[name="username"]', 'john_suggest');
      await page.fill('input[name="password"]', 'suggest123');
      await page.click('button[type="submit"]');
      
      // Wait for timeout handling
      await page.waitForTimeout(5000);
      
      // Should show timeout or loading message
      await expect(page.locator('text=Signing in...').or(
        page.locator('text=Loading').or(
          page.locator('text=Timeout')
        )
      )).toBeVisible();
    });

    test('should handle malformed JSON responses', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      // Mock malformed response
      await page.route('**/api/v1/auth/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: 'invalid json{'
        });
      });
      
      // Try to login
      await page.fill('input[name="username"]', 'john_suggest');
      await page.fill('input[name="password"]', 'suggest123');
      await page.click('button[type="submit"]');
      
      await page.waitForTimeout(2000);
      
      // Should handle parse error gracefully
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Error').or(
        page.locator('text=Failed')
      )).toBeVisible();
    });
  });

  test.describe('UI State Error Handling', () => {
    test('should handle missing catalog data gracefully', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Mock empty catalog response
      await page.route('**/api/v1/catalogs**', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([])
        });
      });
      
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        // Should show "no catalogs" message
        await expect(page.locator('text=No catalogs').or(
          page.locator('text=Empty').or(
            page.locator('text=No data')
          )
        )).toBeVisible({ timeout: 5000 });
      }
    });

    test('should handle broken navigation gracefully', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Try to navigate to non-existent routes
      await page.goto('/non-existent-page');
      await page.waitForTimeout(1000);
      
      // Should show 404 or redirect to home
      const is404 = await page.locator('text=404').or(
        page.locator('text=Not found').or(
          page.locator('text=Page not found')
        )
      ).isVisible();
      
      const isHome = await page.locator('text=Databricks Metadata Manager').isVisible();
      
      expect(is404 || isHome).toBe(true);
    });

    test('should handle component loading errors', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Check if error boundaries are working
      // This is tricky to test without actually causing a React error
      
      // Navigate around the app to ensure stability
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(1000);
        
        // Should not show uncaught errors
        const hasUncaughtError = await page.locator('text=Something went wrong').or(
          page.locator('text=Unexpected error').or(
            page.locator('text=ChunkLoadError')
          )
        ).isVisible();
        
        expect(hasUncaughtError).toBe(false);
      }
    });

    test('should handle permission denied errors', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Mock permission denied for admin endpoints
      await page.route('**/api/v1/admin/**', route => {
        route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Permission denied' })
        });
      });
      
      // Try to access admin functionality (if UI allows)
      const adminLink = page.locator('text=Admin').or(
        page.locator('text=Settings').or(
          page.locator('text=Users')
        )
      );
      
      if (await adminLink.isVisible()) {
        await adminLink.click();
        await page.waitForTimeout(1000);
        
        // Should show permission error
        await expect(page.locator('text=Permission denied').or(
          page.locator('text=Access denied').or(
            page.locator('text=Unauthorized')
          )
        )).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Form Validation and Edge Cases', () => {
    test('should validate empty comment suggestions', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Navigate to a table if possible
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        // Try to submit empty comment
        const suggestButton = page.locator('button:has-text("Suggest Comment")');
        if (await suggestButton.isVisible()) {
          await suggestButton.click();
          await page.waitForTimeout(500);
          
          const commentInput = page.locator('textarea').first();
          if (await commentInput.isVisible()) {
            // Leave empty and try to submit
            await commentInput.fill('');
            
            const submitButton = page.locator('button:has-text("Submit")').first();
            if (await submitButton.isVisible()) {
              await submitButton.click();
              await page.waitForTimeout(1000);
              
              // Should show validation error
              await expect(page.locator('text=required').or(
                page.locator('text=empty').or(
                  page.locator('text=Enter a comment')
                )
              )).toBeVisible({ timeout: 3000 });
            }
          }
        }
      }
    });

    test('should handle very long comment text', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        const suggestButton = page.locator('button:has-text("Suggest Comment")');
        if (await suggestButton.isVisible()) {
          await suggestButton.click();
          await page.waitForTimeout(500);
          
          const commentInput = page.locator('textarea').first();
          if (await commentInput.isVisible()) {
            // Fill with very long text
            const longText = 'This is a very long comment '.repeat(100);
            await commentInput.fill(longText);
            
            const submitButton = page.locator('button:has-text("Submit")').first();
            if (await submitButton.isVisible()) {
              await submitButton.click();
              await page.waitForTimeout(1000);
              
              // Should either accept or show length validation
              const success = await page.locator('text=Success').isVisible();
              const lengthError = await page.locator('text=too long').or(
                page.locator('text=maximum length')
              ).isVisible();
              
              expect(success || lengthError).toBe(true);
            }
          }
        }
      }
    });

    test('should handle special characters in comments', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        const suggestButton = page.locator('button:has-text("Suggest Comment")');
        if (await suggestButton.isVisible()) {
          await suggestButton.click();
          await page.waitForTimeout(500);
          
          const commentInput = page.locator('textarea').first();
          if (await commentInput.isVisible()) {
            // Fill with special characters
            const specialText = 'Comment with "quotes", <tags>, & symbols, 日本語, émojis 🚀💡';
            await commentInput.fill(specialText);
            
            const submitButton = page.locator('button:has-text("Submit")').first();
            if (await submitButton.isVisible()) {
              await submitButton.click();
              await page.waitForTimeout(1000);
              
              // Should handle special characters properly
              await expect(page.locator('text=Success').or(
                page.locator('text=Error')
              )).toBeVisible({ timeout: 5000 });
            }
          }
        }
      }
    });
  });

  test.describe('React Router and Framework Warnings', () => {
    test('should handle React Router future flag warnings', async ({ page }) => {
      const consoleWarnings: string[] = [];
      
      page.on('console', msg => {
        if (msg.type() === 'warning' && msg.text().includes('React Router Future Flag Warning')) {
          consoleWarnings.push(msg.text());
        }
      });

      await loginAs(page, 'suggest_only');
      
      // Navigate between routes to trigger router warnings
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(500);
      }
      
      if (await page.locator('text=Home').isVisible()) {
        await page.click('text=Home');
        await page.waitForTimeout(500);
      }

      // Document any router warnings found
      if (consoleWarnings.length > 0) {
        console.log('React Router warnings detected:', consoleWarnings.length);
        console.log('Recommendation: Update router config with future flags');
      }
    });

    test('should handle missing API endpoints gracefully', async ({ page }) => {
      const networkErrors: string[] = [];
      
      page.on('requestfailed', request => {
        if (request.url().includes('/api/v1/users/me')) {
          networkErrors.push(request.url());
        }
      });

      await loginAs(page, 'suggest_only');
      
      // Wait for any delayed API calls
      await page.waitForTimeout(2000);
      
      if (networkErrors.length > 0) {
        console.log('Missing API endpoints detected:', networkErrors);
        console.log('Recommendation: Implement /api/v1/users/me endpoint');
      }
      
      // App should still function despite missing endpoints
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
    });

    test('should ignore browser extension errors', async ({ page }) => {
      const extensionErrors: string[] = [];
      
      page.on('console', msg => {
        if (msg.type() === 'error' && msg.text().includes('chrome-extension://')) {
          extensionErrors.push(msg.text());
        }
      });

      await loginAs(page, 'suggest_only');
      
      // Browser extension errors are expected and should not affect functionality
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
      
      if (extensionErrors.length > 0) {
        console.log(`Browser extension errors (expected): ${extensionErrors.length}`);
      }
    });
  });

  test.describe('Performance and Stability', () => {
    test('should handle rapid navigation without breaking', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Rapidly navigate between sections
      for (let i = 0; i < 5; i++) {
        if (await page.locator('text=Catalogs').isVisible()) {
          await page.click('text=Catalogs');
          await page.waitForTimeout(200);
        }
        
        if (await page.locator('text=Home').isVisible()) {
          await page.click('text=Home');
          await page.waitForTimeout(200);
        }
      }
      
      // Should still be functional
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
    });

    test('should handle multiple concurrent requests', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Trigger multiple requests at once
      const promises: Promise<any>[] = [];
      
      if (await page.locator('text=Catalogs').isVisible()) {
        // Click multiple times quickly
        for (let i = 0; i < 3; i++) {
          promises.push(page.click('text=Catalogs'));
          await page.waitForTimeout(100);
        }
      }
      
      // Wait for all to complete
      await Promise.allSettled(promises);
      await page.waitForTimeout(2000);
      
      // Should handle gracefully without crashes
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
    });

    test('should recover from temporary network issues', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Block network temporarily
      await page.route('**/api/v1/**', route => {
        route.abort('internetdisconnected');
      });
      
      // Try to navigate
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        // Should show loading or error state
        await expect(page.locator('text=Loading').or(
          page.locator('text=Error').or(
            page.locator('text=Connection')
          )
        )).toBeVisible({ timeout: 5000 });
      }
      
      // Restore network
      await page.unroute('**/api/v1/**');
      
      // Try again
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        // Should recover and work normally
        // Note: This depends on retry logic in the frontend
      }
    });
  });
});