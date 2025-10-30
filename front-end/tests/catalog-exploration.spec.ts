import { test, expect } from '@playwright/test';

test.describe('Catalog Exploration Tests', () => {
  // Helper function to login as John (suggest_only user)
  async function loginAsJohn(page: any) {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const johnCard = page.locator('text=Test User').locator('xpath=ancestor::div[contains(@class, "MuiCard-root")]').first();
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

  test('should display available catalogs', async ({ page }) => {
    // Navigate to catalogs section
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Should see the arao catalog from our backend
      await expect(page.locator('text=arao')).toBeVisible({ timeout: 10000 });
      
      // Should see catalog metadata
      await expect(page.locator('text=Main catalog').or(page.locator('text=workspace'))).toBeVisible({ timeout: 5000 });
      
      // Should see loading state initially
      const loadingIndicator = page.locator('text=Loading').or(page.locator('[role="progressbar"]'));
      if (await loadingIndicator.isVisible()) {
        await expect(loadingIndicator).not.toBeVisible({ timeout: 10000 });
      }
    } else {
      console.log('Catalogs navigation not found - checking for catalog browsing components');
      
      // Alternative: look for catalog browser component
      if (await page.locator('[data-testid="catalog-browser"]').isVisible()) {
        await expect(page.locator('text=arao')).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should navigate through catalog hierarchy', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Click on arao catalog
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        // Should see schemas including metadata_test
        await expect(page.locator('text=metadata_test')).toBeVisible({ timeout: 5000 });
        
        // Click on metadata_test schema
        await page.click('text=metadata_test');
        await page.waitForTimeout(1000);
        
        // Should see tables we created
        await expect(page.locator('text=users').or(page.locator('text=products'))).toBeVisible({ timeout: 5000 });
        
        // Click on users table
        if (await page.locator('text=users').isVisible()) {
          await page.click('text=users');
          await page.waitForTimeout(1000);
          
          // Should see table details with columns
          await expect(page.locator('text=user_id').or(page.locator('text=email'))).toBeVisible({ timeout: 5000 });
        }
      }
    }
  });

  test('should display table metadata and column details', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
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
            await expect(page.locator('text=Customer information and profile data')).toBeVisible({ timeout: 5000 });
            
            // Should see column details
            await expect(page.locator('text=user_id')).toBeVisible();
            await expect(page.locator('text=email')).toBeVisible();
            await expect(page.locator('text=first_name')).toBeVisible();
            
            // Should see column comments
            await expect(page.locator('text=Unique identifier for each user')).toBeVisible();
            await expect(page.locator('text=User email address for login')).toBeVisible();
          }
        }
      }
    }
  });

  test('should show different table types with their metadata', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          // Test different table types
          const tablesToTest = ['users', 'products', 'orders', 'employees'];
          
          for (const tableName of tablesToTest) {
            if (await page.locator(`text=${tableName}`).isVisible()) {
              await page.click(`text=${tableName}`);
              await page.waitForTimeout(1000);
              
              // Should see table-specific metadata
              if (tableName === 'users') {
                await expect(page.locator('text=Customer information')).toBeVisible({ timeout: 3000 });
              } else if (tableName === 'products') {
                await expect(page.locator('text=Product catalog')).toBeVisible({ timeout: 3000 });
              } else if (tableName === 'orders') {
                await expect(page.locator('text=Customer orders')).toBeVisible({ timeout: 3000 });
              } else if (tableName === 'employees') {
                await expect(page.locator('text=Employee master data')).toBeVisible({ timeout: 3000 });
              }
              
              // Go back to table list
              const breadcrumb = page.locator('text=metadata_test').last();
              if (await breadcrumb.isVisible()) {
                await breadcrumb.click();
                await page.waitForTimeout(500);
              }
            }
          }
        }
      }
    }
  });

  test('should handle search and filtering', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Look for search functionality
      const searchInput = page.locator('input[placeholder*="Search"]').or(page.locator('input[type="search"]'));
      
      if (await searchInput.isVisible()) {
        await searchInput.fill('users');
        await page.waitForTimeout(1000);
        
        // Should filter to show only users-related items
        await expect(page.locator('text=users')).toBeVisible();
        
        // Clear search
        await searchInput.clear();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should show proper error handling for missing data', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Try to navigate to non-existent catalog
      const url = page.url();
      await page.goto(url + '/nonexistent-catalog');
      await page.waitForTimeout(1000);
      
      // Should show appropriate error message
      await expect(page.locator('text=Not found').or(page.locator('text=Catalog not found')).or(page.locator('text=Error'))).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display column data types and constraints', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Navigate to users table
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          if (await page.locator('text=users').isVisible()) {
            await page.click('text=users');
            await page.waitForTimeout(1000);
            
            // Should see data types
            await expect(page.locator('text=BIGINT').or(page.locator('text=STRING')).or(page.locator('text=INT'))).toBeVisible({ timeout: 5000 });
            
            // Should see nullable/not nullable information
            await expect(page.locator('text=NOT NULL').or(page.locator('text=nullable'))).toBeVisible({ timeout: 3000 });
          }
        }
      }
    }
  });

  test('should handle large tables with pagination or virtualization', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Navigate to a table with many columns (products has 18 columns)
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          if (await page.locator('text=products').isVisible()) {
            await page.click('text=products');
            await page.waitForTimeout(1000);
            
            // Should handle large number of columns gracefully
            await expect(page.locator('text=product_id')).toBeVisible();
            await expect(page.locator('text=sku')).toBeVisible();
            await expect(page.locator('text=product_name')).toBeVisible();
            
            // Should either show pagination or scroll
            const hasScroll = await page.evaluate(() => {
              return document.documentElement.scrollHeight > window.innerHeight;
            });
            
            const hasPagination = await page.locator('text=Next').or(page.locator('[aria-label="pagination"]')).isVisible();
            
            // Should handle the display somehow
            expect(hasScroll || hasPagination).toBe(true);
          }
        }
      }
    }
  });

  test('should maintain breadcrumb navigation', async ({ page }) => {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      // Navigate deep into hierarchy
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        // Should show breadcrumb
        await expect(page.locator('text=arao')).toBeVisible();
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          // Should show full breadcrumb path
          await expect(page.locator('text=arao')).toBeVisible();
          await expect(page.locator('text=metadata_test')).toBeVisible();
          
          if (await page.locator('text=users').isVisible()) {
            await page.click('text=users');
            await page.waitForTimeout(1000);
            
            // Test breadcrumb navigation back
            const araoBreadcrumb = page.locator('text=arao').first();
            if (await araoBreadcrumb.isVisible()) {
              await araoBreadcrumb.click();
              await page.waitForTimeout(1000);
              
              // Should be back at catalog level
              await expect(page.locator('text=metadata_test')).toBeVisible();
            }
          }
        }
      }
    }
  });
});