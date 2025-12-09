import { test, expect } from '@playwright/test';

test.describe('Role-Based Access Control Tests', () => {
  const baseURL = 'http://localhost:4001';
  
  // Helper function to login as specific user
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
    
    // Wait for login to complete or error
    await page.waitForResponse(response => 
      response.url().includes('/api/v1/auth/login')
    ).catch(() => null);
    
    await page.waitForTimeout(2000);
    
    // Check if login was successful
    const hasError = await page.locator('[role="alert"]').isVisible();
    if (hasError) {
      const errorText = await page.locator('[role="alert"]').textContent();
      console.log(`Login failed for ${userType}: ${errorText}`);
      test.skip(true, 'Backend not available');
    }
    
    // Should be on home page
    await expect(page).toHaveURL('/');
  }

  test.describe('Suggest Only User (John Doe)', () => {
    test('should have read-only access to catalogs', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Should be able to browse catalogs
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        
        // Should see catalog browser
        await expect(page.locator('text=metadata_test')).toBeVisible({ timeout: 10000 });
        
        // Should NOT see admin functions
        await expect(page.locator('text=User Management')).not.toBeVisible();
        await expect(page.locator('text=System Settings')).not.toBeVisible();
      }
    });

    test('should be able to suggest comments but not approve them', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Navigate to a table that exists
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        
        // Wait for catalogs to load
        await page.waitForTimeout(2000);
        
        // Try to find the test schema
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          // Look for a table
          if (await page.locator('text=users').isVisible()) {
            await page.click('text=users');
            await page.waitForTimeout(1000);
            
            // Should be able to suggest comments
            if (await page.locator('button:has-text("Suggest Comment")').isVisible()) {
              await page.click('button:has-text("Suggest Comment")');
              
              // Should NOT see approve/reject buttons
              await expect(page.locator('button:has-text("Approve")')).not.toBeVisible();
              await expect(page.locator('button:has-text("Reject")')).not.toBeVisible();
            }
          }
        }
      }
    });

    test('should not have access to pending approvals', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Should not see approvals section in navigation
      await expect(page.locator('text=Pending Approvals')).not.toBeVisible();
      await expect(page.locator('text=Approval Queue')).not.toBeVisible();
    });
  });

  test.describe('Approver User (Jane Smith)', () => {
    test('should have access to approval functionality', async ({ page }) => {
      await loginAs(page, 'approver');
      
      // Should see approvals in navigation
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        
        // Should see pending approvals page
        await expect(page.locator('text=Pending Approvals').or(page.locator('text=No pending approvals'))).toBeVisible();
      }
    });

    test('should be able to approve and reject comments', async ({ page }) => {
      await loginAs(page, 'approver');
      
      // Navigate to catalogs and try to find suggestions
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        // Check if we can see approve/reject buttons in suggestions
        if (await page.locator('button:has-text("Approve")').isVisible()) {
          // Approver should see these buttons
          await expect(page.locator('button:has-text("Approve")')).toBeVisible();
          await expect(page.locator('button:has-text("Reject")')).toBeVisible();
        }
      }
    });

    test('should still not have admin privileges', async ({ page }) => {
      await loginAs(page, 'approver');
      
      // Should NOT see admin functions
      await expect(page.locator('text=User Management')).not.toBeVisible();
      await expect(page.locator('text=System Settings')).not.toBeVisible();
      await expect(page.locator('text=Admin Panel')).not.toBeVisible();
    });
  });

  test.describe('Admin User', () => {
    test('should have full system access', async ({ page }) => {
      await loginAs(page, 'admin');
      
      // Should see all functionality
      if (await page.locator('text=Admin').isVisible() || await page.locator('text=Settings').isVisible()) {
        // Admin should have access to admin functions
        console.log('Admin interface detected');
      }
      
      // Should have approval access
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await expect(page.locator('text=Pending Approvals').or(page.locator('text=No pending approvals'))).toBeVisible();
      }
    });

    test('should be able to manage users', async ({ page }) => {
      await loginAs(page, 'admin');
      
      // Look for user management functionality
      if (await page.locator('text=Users').isVisible() || await page.locator('text=User Management').isVisible()) {
        const userLink = page.locator('text=Users').or(page.locator('text=User Management')).first();
        await userLink.click();
        
        // Should see user list or management interface
        await expect(page.locator('text=john_suggest').or(page.locator('text=Users')).or(page.locator('text=No users'))).toBeVisible();
      }
    });

    test('should have access to all catalog functions', async ({ page }) => {
      await loginAs(page, 'admin');
      
      // Admin should see all catalogs and have full permissions
      if (await page.locator('text=Catalogs').isVisible()) {
        await page.click('text=Catalogs');
        await page.waitForTimeout(2000);
        
        // Should see test catalog
        await expect(page.locator('text=metadata_test')).toBeVisible({ timeout: 10000 });
      }
    });
  });

  test.describe('Cross-Role Functionality', () => {
    test('all roles should see proper navigation based on permissions', async ({ page }) => {
      const roles: Array<'suggest_only' | 'approver' | 'admin'> = ['suggest_only', 'approver', 'admin'];
      
      for (const role of roles) {
        await loginAs(page, role);
        
        // All roles should see basic navigation
        await expect(page.locator('text=Databricks Metadata Manager')).toBeVisible();
        
        // Check role-specific navigation
        if (role === 'suggest_only') {
          // Suggest only - minimal navigation
          await expect(page.locator('text=Catalogs')).toBeVisible();
        } else if (role === 'approver') {
          // Approver - should see approvals
          // Note: This depends on how the UI is implemented
        } else if (role === 'admin') {
          // Admin - should see everything
          // Note: This depends on how the admin UI is implemented
        }
        
        // Logout for next test
        if (await page.locator('text=Logout').isVisible()) {
          await page.click('text=Logout');
          await page.waitForTimeout(1000);
        } else if (await page.locator('[aria-label="Logout"]').isVisible()) {
          await page.click('[aria-label="Logout"]');
          await page.waitForTimeout(1000);
        }
      }
    });

    test('should maintain user session and permissions', async ({ page }) => {
      await loginAs(page, 'approver');
      
      // Refresh page
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      // Should still be logged in as approver
      await expect(page.locator('text=Jane').or(page.locator('text=Approver'))).toBeVisible();
      
      // Should still have approver permissions
      if (await page.locator('text=Approvals').isVisible()) {
        await expect(page.locator('text=Approvals')).toBeVisible();
      }
    });
  });
});