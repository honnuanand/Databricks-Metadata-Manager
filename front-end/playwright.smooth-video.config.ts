import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4001',
    trace: 'off',
    screenshot: 'only-on-failure',
    video: {
      mode: 'on',
      size: { width: 1920, height: 1080 }
    },
    // Reduce animations and transitions
    launchOptions: {
      args: [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu-sandbox',
        '--force-color-profile=srgb',
      ],
      // Slow down execution for smoother video
      slowMo: 100,
    },
    // Add consistent viewport
    viewport: { width: 1920, height: 1080 },
    // Disable animations in browser
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Additional Chrome-specific settings for smooth rendering
        launchOptions: {
          args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu-sandbox',
            '--force-device-scale-factor=1',
            '--high-dpi-support=1',
            '--force-color-profile=srgb',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceInProcess',
            '--window-size=1920,1080',
          ],
          slowMo: 100,
        },
      },
    },
  ],
});