import { test, expect } from '@playwright/test';

test.describe('Catalog Explorer and Comment Workflow', () => {
  test('Explore catalog hierarchy and add comment', async ({ page }) => {
    test.setTimeout(120000); // 2 minutes
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // LOGIN
    // ============================================
    console.log('🔐 Logging in...');
    await page.goto('http://localhost:4001');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Login
    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);
    console.log('✓ Login successful');

    // ============================================
    // NAVIGATE TO CATALOG EXPLORER
    // ============================================
    console.log('📂 Navigating to Catalog Explorer...');

    // Click on Catalog Explorer in sidebar
    const catalogLink = page.locator('text=Catalog Explorer').first();
    await catalogLink.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    console.log('✓ On Catalog Explorer page');

    // ============================================
    // EXPAND ARAO CATALOG
    // ============================================
    console.log('📁 Expanding arao catalog...');
    await page.waitForTimeout(2000);

    // Click on arao catalog
    const araoElement = page.locator('text=arao').first();
    await araoElement.click();
    await page.waitForTimeout(3000);
    console.log('✓ Arao catalog expanded');

    // ============================================
    // EXPAND METADATA_TEST SCHEMA
    // ============================================
    console.log('📊 Expanding metadata_test schema...');
    await page.waitForTimeout(2000);

    // Click on metadata_test schema
    await page.locator('text=metadata_test').first().click();
    await page.waitForTimeout(3000);
    console.log('✓ metadata_test schema expanded');

    // Scroll to see tables
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(1000);

    // ============================================
    // SELECT USERS TABLE
    // ============================================
    console.log('📋 Selecting users table...');
    await page.waitForTimeout(1000);

    // Click on users table
    await page.locator('text=users').first().click();

    // Wait for table viewer to load
    await page.waitForSelector('[data-testid="table-viewer"]', { timeout: 10000 });
    await page.waitForTimeout(3000);
    console.log('✓ Users table loaded');

    // ============================================
    // ADD COMMENT SUGGESTION
    // ============================================
    console.log('💬 Adding comment suggestion...');

    // Scroll to see columns
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);

    // Find and click suggest comment button
    const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();
    await suggestButton.click();
    await page.waitForTimeout(2000);

    // Fill in the comment
    const commentField = page.locator('textarea').first();
    await commentField.fill('This is the primary key column for the users table. It uniquely identifies each user record in the system and is auto-incremented.');
    await page.waitForTimeout(1500);

    // Submit the comment
    await page.click('[data-testid="submit-suggestion-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Comment suggestion submitted');

    // ============================================
    // FINAL VIEW
    // ============================================
    console.log('🎉 WORKFLOW DEMONSTRATION COMPLETE!');

    // Scroll to top for final view
    await page.mouse.wheel(0, -500);
    await page.waitForTimeout(2000);

    // Take final screenshot
    await page.screenshot({ path: 'test-videos/catalog-workflow-complete.png' });

    // Final pause for video
    await page.waitForTimeout(3000);

    console.log('═════════════════════════════════════════════════');
    console.log('✅ Catalog exploration and comment workflow done!');
    console.log('═════════════════════════════════════════════════');
  });
});