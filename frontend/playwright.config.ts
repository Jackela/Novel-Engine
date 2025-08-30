import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Emergent Narrative Dashboard UAT
 * 
 * Comprehensive testing configuration supporting:
 * - Multi-browser testing (Chrome, Firefox, Safari)
 * - Mobile and desktop viewports
 * - Real-time WebSocket testing
 * - Visual regression testing
 * - Performance monitoring
 */

export default defineConfig({
  testDir: './tests/e2e',
  
  // Global test settings
  timeout: 60 * 1000, // 60 seconds for complex dashboard operations
  expect: {
    timeout: 10 * 1000, // 10 seconds for assertions
  },
  
  // Test execution settings
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined, // Use single worker in CI for stability
  
  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'junit-results.xml' }],
    ['list'],
  ],
  
  // Global test settings
  use: {
    // Base URL for testing
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    
    // Browser settings
    headless: process.env.CI ? true : false,
    viewport: { width: 1440, height: 900 }, // Desktop default
    ignoreHTTPSErrors: true,
    
    // Performance and debugging
    actionTimeout: 10 * 1000,
    navigationTimeout: 30 * 1000,
    
    // Screenshots and videos
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    
    // Locale settings
    locale: 'en-US',
    timezoneId: 'America/New_York',
  },

  // Project configurations for different browsers and devices
  projects: [
    {
      name: 'chromium-desktop',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        contextOptions: {
          // Enable real-time features
          permissions: ['notifications'],
        },
      },
    },

    {
      name: 'firefox-desktop',
      use: { 
        ...devices['Desktop Firefox'],
        viewport: { width: 1440, height: 900 },
      },
    },

    {
      name: 'webkit-desktop',
      use: { 
        ...devices['Desktop Safari'],
        viewport: { width: 1440, height: 900 },
      },
    },

    // Tablet testing for responsive design
    {
      name: 'tablet',
      use: { 
        ...devices['iPad Pro'],
        viewport: { width: 1024, height: 768 },
      },
    },

    // Mobile testing
    {
      name: 'mobile',
      use: { 
        ...devices['iPhone 13'],
        viewport: { width: 375, height: 667 },
      },
    },

    // High DPI testing
    {
      name: 'high-dpi',
      use: {
        ...devices['Desktop Chrome HiDPI'],
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
      },
    },
  ],

  // Development server configuration
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000, // 2 minutes to start dev server
    env: {
      NODE_ENV: 'test',
      REACT_APP_API_BASE_URL: process.env.TEST_API_URL || 'http://localhost:8000/v1',
      REACT_APP_WS_URL: process.env.TEST_WS_URL || 'ws://localhost:8001/ws',
    },
  },

  // Global setup and teardown
  globalSetup: './tests/e2e/setup/global-setup.ts',
  globalTeardown: './tests/e2e/setup/global-teardown.ts',
  
  // Test result directories
  outputDir: 'test-results/',
  
  // Experimental features
  experimental: {
    // Enable test isolation
    testIdAttribute: 'data-testid',
  },
});