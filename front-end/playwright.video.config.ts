import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 120 * 1000,
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:4001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',

    // Video recording settings
    video: {
      mode: 'on',
      size: { width: 1920, height: 1080 }
    },

    // Slower actions for better video visibility
    actionTimeout: 10000,
    navigationTimeout: 30000,

    // Slow down actions by 500ms for better video
    launchOptions: {
      slowMo: 500,
    },
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
        // Record video in videos folder
        video: {
          mode: 'on',
          size: { width: 1920, height: 1080 }
        }
      },
    },
  ],

  outputDir: './test-results/',
});