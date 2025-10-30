import { defineConfig, devices } from '@playwright/test';

// Support testing against deployed Databricks app or local dev server
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4001';
const isLocalDev = baseURL.includes('localhost');

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    // Increase timeouts for deployed apps (SSO redirects, etc.)
    actionTimeout: isLocalDev ? 10000 : 30000,
    navigationTimeout: isLocalDev ? 30000 : 60000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile tests
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Run your local dev server before starting the tests (only for local dev)
  webServer: isLocalDev ? {
    command: 'npm run dev',
    url: 'http://localhost:4001',
    reuseExistingServer: !process.env.CI,
  } : undefined,
});