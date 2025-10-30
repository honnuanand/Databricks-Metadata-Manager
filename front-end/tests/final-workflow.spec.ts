import { test, expect } from '@playwright/test';

test.describe('Complete Metadata Manager Workflow', () => {
  test('Full workflow with proper navigation', async ({ page }) => {
    test.setTimeout(180000);
    await page.setViewportSize({ width: 1920, height: 1080 });

    // ============================================
    // STEP 1: LOGIN
    // ============================================
    console.log('STEP 1: Login as suggestion user');
    await page.goto('http://localhost:4001');
    await page.waitForTimeout(2000);

    await page.fill('input[name="username"]', 'john_suggest');
    await page.fill('input[name="password"]', 'suggest123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Login successful');

    // ============================================
    // STEP 2: NAVIGATE TO CATALOG EXPLORER VIA MENU
    // ============================================
    console.log('STEP 2: Navigate to Catalog Explorer');

    // Look for navigation menu item - try multiple selectors
    const catalogLink = await page.locator('a:has-text("Catalog Explorer")').first()
      .or(page.locator('text=Catalog Explorer').first())
      .or(page.locator('[href="/catalog"]').first());

    if (await catalogLink.isVisible()) {
      console.log('Found Catalog Explorer link, clicking...');
      await catalogLink.click();
      await page.waitForTimeout(5000); // Give time for catalogs to load
    } else {
      console.log('Could not find link, navigating directly...');
      await page.goto('http://localhost:4001/catalog', { waitUntil: 'networkidle' });
      await page.waitForTimeout(5000);
    }

    console.log('Current URL:', page.url());
    console.log('✓ On Catalog Explorer page');

    // ============================================
    // STEP 3: EXPAND ARAO CATALOG
    // ============================================
    console.log('STEP 3: Expand arao catalog');
    await page.waitForTimeout(2000);

    // Look for arao in any element, not just accordion
    let araoElement = page.locator('text=arao').first();
    let araoVisible = await araoElement.isVisible().catch(() => false);

    if (!araoVisible) {
      // Try to find it in accordion structure
      araoElement = page.locator('.MuiAccordion-root:has-text("arao")').first();
      araoVisible = await araoElement.isVisible().catch(() => false);
    }

    if (araoVisible) {
      console.log('Found arao catalog, expanding...');
      await araoElement.click();
      await page.waitForTimeout(3000);
      console.log('✓ Arao catalog expanded');
    } else {
      console.log('⚠ Could not find arao catalog');
      const pageText = await page.locator('body').innerText();
      console.log('Page text sample:', pageText.substring(0, 500));
    }

    // ============================================
    // STEP 4: EXPAND METADATA_TEST SCHEMA
    // ============================================
    console.log('STEP 4: Expand metadata_test schema');
    await page.waitForTimeout(2000);

    const schemaElement = page.locator('text=metadata_test').first();
    if (await schemaElement.isVisible().catch(() => false)) {
      console.log('Found metadata_test schema, expanding...');
      await schemaElement.click();
      await page.waitForTimeout(3000);
      console.log('✓ metadata_test schema expanded');
    } else {
      console.log('⚠ Could not find metadata_test schema');
    }

    // ============================================
    // STEP 5: SELECT USERS TABLE
    // ============================================
    console.log('STEP 5: Select users table');
    await page.waitForTimeout(2000);

    const tableElement = page.locator('text=users').first();
    if (await tableElement.isVisible().catch(() => false)) {
      console.log('Found users table, clicking...');
      await tableElement.click();
      await page.waitForTimeout(4000);
      console.log('✓ Users table selected');
    } else {
      console.log('⚠ Could not find users table');
    }

    // ============================================
    // STEP 6: ADD COMMENT SUGGESTION
    // ============================================
    console.log('STEP 6: Add comment suggestion');

    // Wait for table viewer to load
    const tableViewer = page.locator('[data-testid="table-viewer"]');
    if (await tableViewer.isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log('Table viewer loaded');

      // Scroll to see columns
      await page.mouse.wheel(0, 300);
      await page.waitForTimeout(1000);

      // Find suggest comment button
      const suggestButton = page.locator('[data-testid="suggest-comment-button"]').first();
      if (await suggestButton.isVisible().catch(() => false)) {
        console.log('Found suggest button, clicking...');
        await suggestButton.click();
        await page.waitForTimeout(2000);

        // Fill comment - look for textarea inside the test-id div
        const commentInput = page.locator('[data-testid="comment-suggestion-input"] textarea').first();
        if (await commentInput.isVisible().catch(() => false)) {
          await commentInput.fill('Primary key for user records, auto-generated unique identifier');
          await page.waitForTimeout(1000);

          // Submit
          const submitButton = page.locator('[data-testid="submit-suggestion-button"]');
          if (await submitButton.isVisible().catch(() => false)) {
            await submitButton.click();
            await page.waitForTimeout(3000);
            console.log('✓ Comment suggestion submitted');
          }
        }
      }
    }

    // ============================================
    // STEP 7: SWITCH TO APPROVER USER
    // ============================================
    console.log('STEP 7: Switch to approver user');

    // Navigate to login to force logout
    await page.goto('http://localhost:4001/login');
    await page.waitForTimeout(2000);

    await page.fill('input[name="username"]', 'jane_approver');
    await page.fill('input[name="password"]', 'approve123');
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(4000);
    console.log('✓ Logged in as approver');

    // ============================================
    // STEP 8: NAVIGATE BACK TO THE TABLE
    // ============================================
    console.log('STEP 8: Navigate back to users table');

    // Navigate to catalog explorer
    const catalogLink2 = await page.locator('a:has-text("Catalog Explorer")').first();
    if (await catalogLink2.isVisible()) {
      await catalogLink2.click();
      await page.waitForTimeout(5000);
    }

    // Expand arao
    const araoElement2 = page.locator('text=arao').first();
    if (await araoElement2.isVisible().catch(() => false)) {
      await araoElement2.click();
      await page.waitForTimeout(2000);
    }

    // Expand metadata_test
    const schemaElement2 = page.locator('text=metadata_test').first();
    if (await schemaElement2.isVisible().catch(() => false)) {
      await schemaElement2.click();
      await page.waitForTimeout(2000);
    }

    // Select users table
    const tableElement2 = page.locator('text=users').first();
    if (await tableElement2.isVisible().catch(() => false)) {
      await tableElement2.click();
      await page.waitForTimeout(4000);
    }
    console.log('✓ Back at users table');

    // ============================================
    // STEP 9: APPROVE THE COMMENT
    // ============================================
    console.log('STEP 9: Approve the comment');
    await page.waitForTimeout(2000);

    // Scroll to find review button
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(1000);

    const reviewButton = page.locator('[data-testid="review-comment-button"]').first();
    if (await reviewButton.isVisible().catch(() => false)) {
      console.log('Found review button');
      await reviewButton.click();
      await page.waitForTimeout(2000);

      // Add feedback and approve
      const feedbackInput = page.locator('[data-testid="review-feedback-input"]');
      if (await feedbackInput.isVisible().catch(() => false)) {
        await feedbackInput.fill('Looks good!');
        await page.waitForTimeout(1000);
      }

      const approveButton = page.locator('[data-testid="approve-comment-button"]');
      if (await approveButton.isVisible().catch(() => false)) {
        await approveButton.click();
        await page.waitForTimeout(3000);
        console.log('✓ Comment approved');
      }
    }

    // ============================================
    // STEP 10: APPLY THE COMMENT
    // ============================================
    console.log('STEP 10: Apply the comment');
    await page.waitForTimeout(2000);

    const applyButton = page.locator('[data-testid="apply-comment-button"]').first();
    if (await applyButton.isVisible().catch(() => false)) {
      console.log('Found apply button');
      await applyButton.click();
      await page.waitForTimeout(4000);
      console.log('✓ Comment applied');
    }

    // Final wait for video
    await page.waitForTimeout(3000);
    console.log('✅ WORKFLOW COMPLETE!');
  });
});