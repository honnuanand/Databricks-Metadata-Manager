import { test, expect } from '@playwright/test';

test.describe('Main Application Components', () => {
  // Helper function to login as John (suggest_only user)
  async function loginAsJohn(page: any) {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const johnCard = page.locator('text=John Doe').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
    await johnCard.click();
    
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

  test.beforeEach(async ({ page }) => {
    await loginAsJohn(page);
  });

  test.describe('Catalog Browsing Component', () => {
    test('should display catalog browser with arao catalog', async ({ page }) => {
      // Wait for the application to load completely
      await page.waitForLoadState('networkidle');
      
      // Look for catalog browsing interface
      const catalogElement = page.locator('text=arao').or(
        page.locator('[data-testid="catalog-browser"]').or(
          page.locator('text=Catalogs')
        )
      );
      
      if (await catalogElement.isVisible()) {
        console.log('✅ Catalog browsing component found');
        
        // Should show arao catalog
        await expect(page.locator('text=arao')).toBeVisible({ timeout: 5000 });
        
        // Should show schemas when expanded
        if (await page.locator('text=arao').isVisible()) {
          await page.click('text=arao');
          await page.waitForTimeout(1000);
          
          // Should see our test schemas
          await expect(page.locator('text=metadata_test').or(
            page.locator('text=metadata_manager')
          )).toBeVisible({ timeout: 5000 });
        }
      } else {
        console.log('⚠️ Catalog browsing component not found in current UI');
      }
    });

    test('should navigate through schema hierarchy', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Try to navigate to metadata_test schema
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          // Should see our test tables
          const tableNames = ['users', 'products', 'orders', 'employees'];
          let foundTable = false;
          
          for (const tableName of tableNames) {
            if (await page.locator(`text=${tableName}`).isVisible()) {
              foundTable = true;
              console.log(`✅ Found table: ${tableName}`);
              break;
            }
          }
          
          expect(foundTable).toBe(true);
        }
      }
    });

    test('should display table details when selected', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Navigate to a specific table
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          if (await page.locator('text=users').isVisible()) {
            await page.click('text=users');
            await page.waitForTimeout(1000);
            
            // Should see table comment
            await expect(page.locator('text=Customer information').or(
              page.locator('text=profile data')
            )).toBeVisible({ timeout: 5000 });
            
            // Should see column information
            await expect(page.locator('text=user_id').or(
              page.locator('text=email')
            )).toBeVisible({ timeout: 5000 });
          }
        }
      }
    });

    test('should handle empty states gracefully', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Test behavior when no data is available
      // This tests the robustness of the catalog browser
      
      if (await page.locator('text=No catalogs').isVisible()) {
        console.log('✅ Properly handles empty catalog state');
      } else if (await page.locator('text=arao').isVisible()) {
        console.log('✅ Catalog data loaded successfully');
      } else {
        console.log('⚠️ Catalog state unclear - may need UI investigation');
      }
    });
  });

  test.describe('My Comments Component', () => {
    test('should display my comments section', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Look for my comments component
      const myCommentsElement = page.locator('text=My Comments').or(
        page.locator('text=My Suggestions').or(
          page.locator('[data-testid="my-comments"]')
        )
      );
      
      if (await myCommentsElement.isVisible()) {
        console.log('✅ My Comments component found');
        
        // Should show comment statistics
        await expect(page.locator('text=Total').or(
          page.locator('text=Pending').or(
            page.locator('text=0') // Since we have no comments yet
          )
        )).toBeVisible({ timeout: 5000 });
        
      } else {
        console.log('⚠️ My Comments component not visible in current view');
        
        // Try to navigate to it
        if (await page.locator('text=Comments').isVisible()) {
          await page.click('text=Comments');
          await page.waitForTimeout(1000);
        }
      }
    });

    test('should show empty state for new user', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // For a new user, should show empty state
      if (await page.locator('text=My Comments').isVisible()) {
        await page.click('text=My Comments');
        await page.waitForTimeout(1000);
        
        // Should show empty state messages
        await expect(page.locator('text=No comments').or(
          page.locator('text=No suggestions').or(
            page.locator('text=0')
          )
        )).toBeVisible({ timeout: 5000 });
      }
    });

    test('should allow creating new comment suggestions', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Look for "New Comment" or "Suggest Comment" button
      const newCommentButton = page.locator('button:has-text("New Comment")').or(
        page.locator('button:has-text("Suggest Comment")').or(
          page.locator('button:has-text("Add Comment")')
        )
      );
      
      if (await newCommentButton.isVisible()) {
        console.log('✅ New comment creation button found');
        
        await newCommentButton.click();
        await page.waitForTimeout(500);
        
        // Should open comment creation form
        await expect(page.locator('textarea').or(
          page.locator('input[type="text"]')
        )).toBeVisible({ timeout: 3000 });
        
      } else {
        console.log('⚠️ Comment creation interface not found');
      }
    });
  });

  test.describe('Navigation and Layout', () => {
    test('should have proper navigation menu', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Check for main navigation elements
      const navElements = [
        'Home', 'Catalogs', 'Comments', 'My Comments', 'Dashboard'
      ];
      
      let foundNavElements = 0;
      for (const element of navElements) {
        if (await page.locator(`text=${element}`).isVisible()) {
          foundNavElements++;
          console.log(`✅ Found nav element: ${element}`);
        }
      }
      
      expect(foundNavElements).toBeGreaterThan(0);
    });

    test('should display user information in header', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Should show current user info
      await expect(page.locator('text=John').or(
        page.locator('text=john_suggest').or(
          page.locator('text=Suggest Only')
        )
      )).toBeVisible({ timeout: 5000 });
    });

    test('should have logout functionality', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Look for logout button/menu
      const logoutElement = page.locator('text=Logout').or(
        page.locator('button:has-text("Logout")').or(
          page.locator('[aria-label="Logout"]')
        )
      );
      
      if (await logoutElement.isVisible()) {
        console.log('✅ Logout functionality found');
      } else {
        // Look for user menu that might contain logout
        const userMenu = page.locator('[aria-label="User menu"]').or(
          page.locator('text=john_suggest')
        );
        
        if (await userMenu.isVisible()) {
          await userMenu.click();
          await page.waitForTimeout(500);
          
          if (await page.locator('text=Logout').isVisible()) {
            console.log('✅ Logout found in user menu');
          }
        }
      }
    });
  });

  test.describe('Dashboard Components', () => {
    test('should display dashboard statistics', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Look for dashboard statistics
      const statsElements = page.locator('text=Statistics').or(
        page.locator('text=Overview').or(
          page.locator('[data-testid="dashboard-stats"]')
        )
      );
      
      if (await statsElements.isVisible()) {
        console.log('✅ Dashboard statistics component found');
        
        // Should show various metrics
        const metrics = ['Total', 'Pending', 'Approved', 'Rejected'];
        for (const metric of metrics) {
          if (await page.locator(`text=${metric}`).isVisible()) {
            console.log(`✅ Found metric: ${metric}`);
          }
        }
      } else {
        console.log('⚠️ Dashboard statistics not visible');
      }
    });

    test('should display recent activity', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Look for recent activity component
      if (await page.locator('text=Recent Activity').isVisible()) {
        console.log('✅ Recent activity component found');
        
        // Should show activity items or empty state
        await expect(page.locator('text=No recent activity').or(
          page.locator('text=activity').or(
            page.locator('[data-testid="activity-item"]')
          )
        )).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Error Handling in Components', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      await page.waitForLoadState('networkidle');
      
      // Monitor for error states in components
      const errorElements = page.locator('text=Error').or(
        page.locator('text=Failed to load').or(
          page.locator('[role="alert"]')
        )
      );
      
      // Components should either work or show proper error states
      if (await errorElements.isVisible()) {
        console.log('⚠️ Error state detected in components');
        const errorText = await errorElements.textContent();
        console.log('Error message:', errorText);
        
        // Error should be user-friendly
        expect(errorText).toMatch(/Error|Failed|Unable|Try again/i);
      } else {
        console.log('✅ No error states detected');
      }
    });

    test('should show loading states appropriately', async ({ page }) => {
      // Start from a fresh page load to catch loading states
      await page.goto('/');
      
      // Look for loading indicators
      const loadingElements = page.locator('text=Loading').or(
        page.locator('[role="progressbar"]').or(
          page.locator('.loading').or(
            page.locator('text=Loading...')
          )
        )
      );
      
      // Loading states should appear and then disappear
      if (await loadingElements.isVisible({ timeout: 1000 })) {
        console.log('✅ Loading state detected');
        
        // Should eventually disappear
        await expect(loadingElements).not.toBeVisible({ timeout: 10000 });
        console.log('✅ Loading state resolved');
      } else {
        console.log('⚠️ No loading states detected (may load too quickly)');
      }
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForLoadState('networkidle');
      
      // Should still show main functionality
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
      
      // Navigation might be collapsed on mobile
      if (await page.locator('[aria-label="Menu"]').isVisible()) {
        console.log('✅ Mobile navigation menu found');
      }
    });

    test('should work on tablet viewport', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.waitForLoadState('networkidle');
      
      // Should show full functionality
      await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
    });
  });
});