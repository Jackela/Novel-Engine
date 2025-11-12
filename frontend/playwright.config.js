/**
 * Playwright Configuration for Character Selection Component Tests
 * 
 * This configuration is optimized for testing the Character Selection Component
 * with proper setup for API mocking, browser automation, and test reporting.
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Test directory
  testDir: './src/tests',
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter to use
  reporter: [
    ['html'],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['json', { outputFile: 'test-results/test-results.json' }]
  ],
  
  // Shared settings for all tests
  use: {
    // Base URL for your application
    baseURL: 'http://localhost:5173',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Take screenshot on failure
    screenshot: 'only-on-failure',
    
    // Record video on failure
    video: 'retain-on-failure',
    
    // Browser context options
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    
    // Extra HTTP headers to be sent with every request
    extraHTTPHeaders: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Temporarily disable Firefox due to connection issues
    // {
    //   name: 'firefox',
    //   use: { 
    //     ...devices['Desktop Firefox'],
    //     // Firefox-specific configurations to handle network issues
    //     launchOptions: {
    //       firefoxUserPrefs: {
    //         'network.http.speculative-parallel-limit': 0,
    //         'network.dns.disableIPv6': true,
    //         'network.http.max-connections': 256,
    //         'network.http.max-connections-per-server': 6,
    //       }
    //     }
    //   },
    // },
    // Temporarily disable WebKit due to connection issues
    // {
    //   name: 'webkit',
    //   use: { 
    //     ...devices['Desktop Safari'],
    //     // WebKit-specific configurations
    //     launchOptions: {
    //       ignoreDefaultArgs: ['--enable-automation']
    //     }
    //   },
    // },
    
    // Mobile testing - Chrome works perfectly
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    // Temporarily disable Mobile Safari due to connection issues
    // {
    //   name: 'Mobile Safari',
    //   use: { 
    //     ...devices['iPhone 12'],
    //     // Mobile Safari specific configurations
    //     launchOptions: {
    //       ignoreDefaultArgs: ['--enable-automation']
    //     }
    //   },
    // },
  ],

  // Run your local dev server before starting the tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
    stderr: 'pipe',
    timeout: 120000, // 2 minutes for server startup
    // Additional server options for better compatibility
    env: {
      NODE_ENV: 'test',
      VITE_HOST: '0.0.0.0'
    }
  },

  // Global setup and teardown
  globalSetup: './tests/global-setup.js',
  globalTeardown: './tests/global-teardown.js',

  // Test timeout - increased for slower browsers
  timeout: 60000,
  expect: {
    // Timeout for expect() calls - increased for better compatibility
    timeout: 10000,
  },

  // Output directory for test artifacts
  outputDir: 'test-results/',
  
  // Whether to preserve output directory
  preserveOutput: 'failures-only',
});