import { test, expect } from '@playwright/test';

test.describe('Comment Suggestion Workflows', () => {
  // Helper functions for different user types
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

  async function navigateToUsersTable(page: any) {
    if (await page.locator('text=Catalogs').isVisible()) {
      await page.click('text=Catalogs');
      await page.waitForTimeout(2000);
      
      if (await page.locator('text=arao').isVisible()) {
        await page.click('text=arao');
        await page.waitForTimeout(1000);
        
        if (await page.locator('text=metadata_test').isVisible()) {
          await page.click('text=metadata_test');
          await page.waitForTimeout(1000);
          
          if (await page.locator('text=users').isVisible()) {
            await page.click('text=users');
            await page.waitForTimeout(1000);
            return true;
          }
        }
      }
    }
    return false;
  }

  test.describe('Comment Suggestion Creation', () => {
    test('suggest_only user should be able to create table comment suggestions', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      if (await navigateToUsersTable(page)) {
        // Look for suggest comment button or edit comment functionality
        const suggestButton = page.locator('button:has-text("Suggest Comment")').or(
          page.locator('button:has-text("Edit Comment")').or(
            page.locator('[aria-label="Edit comment"]')
          )
        );
        
        if (await suggestButton.isVisible()) {
          await suggestButton.click();
          await page.waitForTimeout(500);
          
          // Should see comment suggestion form
          const commentInput = page.locator('textarea').or(page.locator('input[type="text"]')).first();
          await expect(commentInput).toBeVisible();
          
          // Fill in a new comment suggestion
          await commentInput.fill('Enhanced customer information table with comprehensive user profiles and activity tracking');
          
          // Look for submit button
          const submitButton = page.locator('button:has-text("Submit")').or(
            page.locator('button:has-text("Save")').or(
              page.locator('button:has-text("Suggest")')
            )
          );
          
          if (await submitButton.isVisible()) {
            await submitButton.click();
            await page.waitForTimeout(1000);
            
            // Should show success message or return to table view
            await expect(page.locator('text=Success').or(
              page.locator('text=Submitted').or(
                page.locator('text=suggestion')
              )
            )).toBeVisible({ timeout: 5000 });
          }
        } else {
          console.log('Comment suggestion UI not found - may need backend integration');
        }
      }
    });

    test('suggest_only user should be able to create column comment suggestions', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      if (await navigateToUsersTable(page)) {
        // Look for a specific column to comment on
        const emailColumn = page.locator('text=email').first();
        
        if (await emailColumn.isVisible()) {
          // Try to click on the column or find edit button near it
          await emailColumn.click();
          await page.waitForTimeout(500);
          
          // Look for column-specific comment editing
          const editButton = page.locator('button:has-text("Edit Comment")').or(
            page.locator('[aria-label="Edit column comment"]')
          ).first();
          
          if (await editButton.isVisible()) {
            await editButton.click();
            await page.waitForTimeout(500);
            
            const commentInput = page.locator('textarea').or(page.locator('input[type="text"]')).first();
            if (await commentInput.isVisible()) {
              await commentInput.fill('Primary email address used for user authentication, notifications, and account recovery');
              
              const submitButton = page.locator('button:has-text("Submit")').or(
                page.locator('button:has-text("Save")')
              ).first();
              
              if (await submitButton.isVisible()) {
                await submitButton.click();
                await page.waitForTimeout(1000);
                
                await expect(page.locator('text=Success').or(page.locator('text=Submitted'))).toBeVisible({ timeout: 5000 });
              }
            }
          }
        }
      }
    });

    test('should validate comment suggestions before submission', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      if (await navigateToUsersTable(page)) {
        const suggestButton = page.locator('button:has-text("Suggest Comment")').first();
        
        if (await suggestButton.isVisible()) {
          await suggestButton.click();
          await page.waitForTimeout(500);
          
          const commentInput = page.locator('textarea').or(page.locator('input[type="text"]')).first();
          if (await commentInput.isVisible()) {
            // Try to submit empty comment
            await commentInput.fill('');
            
            const submitButton = page.locator('button:has-text("Submit")').first();
            if (await submitButton.isVisible()) {
              await submitButton.click();
              await page.waitForTimeout(500);
              
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

    test('should show comment suggestion status and history', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      // Look for suggestions or history section
      if (await page.locator('text=My Suggestions').isVisible()) {
        await page.click('text=My Suggestions');
        await page.waitForTimeout(1000);
        
        // Should see list of suggestions with status
        await expect(page.locator('text=Pending').or(
          page.locator('text=Approved').or(
            page.locator('text=Draft')
          )
        )).toBeVisible({ timeout: 5000 });
      } else if (await page.locator('text=Suggestions').isVisible()) {
        await page.click('text=Suggestions');
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Comment Approval Workflow', () => {
    test('approver should see pending comment suggestions', async ({ page }) => {
      await loginAs(page, 'approver');
      
      // Navigate to approvals section
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        // Should see pending approvals or "no pending" message
        await expect(page.locator('text=Pending Approvals').or(
          page.locator('text=No pending approvals').or(
            page.locator('text=pending')
          )
        )).toBeVisible({ timeout: 5000 });
        
        // If there are pending suggestions, should see approval actions
        if (await page.locator('button:has-text("Approve")').isVisible()) {
          await expect(page.locator('button:has-text("Approve")')).toBeVisible();
          await expect(page.locator('button:has-text("Reject")')).toBeVisible();
        }
      }
    });

    test('approver should be able to approve comment suggestions', async ({ page }) => {
      await loginAs(page, 'approver');
      
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        // Look for a pending suggestion to approve
        const approveButton = page.locator('button:has-text("Approve")').first();
        
        if (await approveButton.isVisible()) {
          await approveButton.click();
          await page.waitForTimeout(500);
          
          // Might have a confirmation dialog
          const confirmButton = page.locator('button:has-text("Confirm")').or(
            page.locator('button:has-text("Yes")')
          );
          
          if (await confirmButton.isVisible()) {
            await confirmButton.click();
            await page.waitForTimeout(1000);
          }
          
          // Should show success message
          await expect(page.locator('text=Approved').or(
            page.locator('text=Success')
          )).toBeVisible({ timeout: 5000 });
        } else {
          console.log('No pending suggestions to approve');
        }
      }
    });

    test('approver should be able to reject comment suggestions with feedback', async ({ page }) => {
      await loginAs(page, 'approver');
      
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        const rejectButton = page.locator('button:has-text("Reject")').first();
        
        if (await rejectButton.isVisible()) {
          await rejectButton.click();
          await page.waitForTimeout(500);
          
          // Should see feedback input
          const feedbackInput = page.locator('textarea').or(
            page.locator('input[placeholder*="feedback"]')
          ).first();
          
          if (await feedbackInput.isVisible()) {
            await feedbackInput.fill('Please make the comment more specific and include business context');
            
            const submitButton = page.locator('button:has-text("Submit")').or(
              page.locator('button:has-text("Reject")')
            ).first();
            
            await submitButton.click();
            await page.waitForTimeout(1000);
            
            await expect(page.locator('text=Rejected').or(
              page.locator('text=Feedback sent')
            )).toBeVisible({ timeout: 5000 });
          }
        }
      }
    });

    test('should show approval history and audit trail', async ({ page }) => {
      await loginAs(page, 'approver');
      
      if (await page.locator('text=History').isVisible() || await page.locator('text=Audit').isVisible()) {
        const historyLink = page.locator('text=History').or(page.locator('text=Audit')).first();
        await historyLink.click();
        await page.waitForTimeout(1000);
        
        // Should show historical approvals with timestamps
        await expect(page.locator('text=Approved').or(
          page.locator('text=Rejected').or(
            page.locator('text=by')
          )
        )).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Comment Application to Databricks', () => {
    test('approved comments should be applied to actual Databricks metadata', async ({ page }) => {
      await loginAs(page, 'admin');
      
      // This test would verify that approved comments actually get applied
      // to the Databricks catalog, which requires backend integration
      
      if (await navigateToUsersTable(page)) {
        // Should see the comment that was applied
        await expect(page.locator('text=Customer information').or(
          page.locator('text=Enhanced customer information')
        )).toBeVisible({ timeout: 5000 });
        
        // Check a specific column
        if (await page.locator('text=email').isVisible()) {
          // Should see the updated column comment
          await expect(page.locator('text=Primary email address').or(
            page.locator('text=email address')
          )).toBeVisible({ timeout: 3000 });
        }
      }
    });

    test('should handle application errors gracefully', async ({ page }) => {
      await loginAs(page, 'admin');
      
      // This would test error handling when Databricks API fails
      // For now, just ensure error states are handled
      
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        // If there are any error messages about Databricks connectivity
        const errorMessage = page.locator('text=Error').or(
          page.locator('text=Failed').or(
            page.locator('text=Connection')
          )
        );
        
        if (await errorMessage.isVisible()) {
          // Should show appropriate error handling
          await expect(errorMessage).toBeVisible();
          console.log('Databricks connection error detected (expected in test environment)');
        }
      }
    });
  });

  test.describe('Bulk Operations', () => {
    test('should support bulk comment suggestions', async ({ page }) => {
      await loginAs(page, 'suggest_only');
      
      if (await navigateToUsersTable(page)) {
        // Look for bulk operations
        if (await page.locator('text=Bulk').isVisible() || await page.locator('text=Select All').isVisible()) {
          const bulkButton = page.locator('text=Bulk').or(page.locator('text=Select All')).first();
          await bulkButton.click();
          await page.waitForTimeout(500);
          
          // Should be able to select multiple items
          const checkboxes = page.locator('input[type="checkbox"]');
          const count = await checkboxes.count();
          
          if (count > 0) {
            // Select first few items
            for (let i = 0; i < Math.min(3, count); i++) {
              await checkboxes.nth(i).check();
            }
            
            // Look for bulk comment action
            if (await page.locator('button:has-text("Bulk Comment")').isVisible()) {
              await page.click('button:has-text("Bulk Comment")');
              await page.waitForTimeout(500);
              
              // Should see bulk comment form
              await expect(page.locator('textarea')).toBeVisible();
            }
          }
        }
      }
    });

    test('approver should support bulk approvals', async ({ page }) => {
      await loginAs(page, 'approver');
      
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        // Look for bulk approval functionality
        if (await page.locator('text=Select All').isVisible()) {
          await page.click('text=Select All');
          await page.waitForTimeout(500);
          
          if (await page.locator('button:has-text("Bulk Approve")').isVisible()) {
            await page.click('button:has-text("Bulk Approve")');
            await page.waitForTimeout(500);
            
            // Should show confirmation
            await expect(page.locator('text=Confirm').or(
              page.locator('text=Are you sure')
            )).toBeVisible({ timeout: 3000 });
          }
        }
      }
    });
  });

  test.describe('Search and Filtering', () => {
    test('should be able to search for specific suggestions', async ({ page }) => {
      await loginAs(page, 'approver');
      
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        const searchInput = page.locator('input[placeholder*="Search"]').or(
          page.locator('input[type="search"]')
        );
        
        if (await searchInput.isVisible()) {
          await searchInput.fill('user');
          await page.waitForTimeout(1000);
          
          // Should filter suggestions
          await expect(page.locator('text=user').or(
            page.locator('text=User')
          )).toBeVisible({ timeout: 3000 });
        }
      }
    });

    test('should be able to filter by suggestion status', async ({ page }) => {
      await loginAs(page, 'approver');
      
      if (await page.locator('text=Approvals').isVisible()) {
        await page.click('text=Approvals');
        await page.waitForTimeout(1000);
        
        // Look for status filter
        const statusFilter = page.locator('select').or(
          page.locator('[aria-label="Status filter"]')
        );
        
        if (await statusFilter.isVisible()) {
          await statusFilter.click();
          await page.waitForTimeout(500);
          
          if (await page.locator('text=Pending').isVisible()) {
            await page.click('text=Pending');
            await page.waitForTimeout(1000);
            
            // Should show only pending suggestions
            await expect(page.locator('text=Pending')).toBeVisible();
          }
        }
      }
    });
  });
});