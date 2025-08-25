/**
 * Playwright Configuration for Novel Engine AI Validation Testing
 * =============================================================
 * 
 * Specialized configuration optimized for comprehensive AI generation validation.
 * This config extends the base Playwright setup with AI-specific timeouts,
 * browser settings, and reporting optimized for real AI testing scenarios.
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Test directory for AI validation tests
  testDir: './src/tests',
  
  // Match only AI validation test files
  testMatch: ['**/ai-generation-validation.spec.js'],
  
  // Run tests sequentially to avoid API rate limiting and resource conflicts
  fullyParallel: false,
  workers: 1, // Single worker to ensure consistent AI testing
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry strategy optimized for AI testing (flaky API calls)
  retries: process.env.CI ? 3 : 2,
  
  // Extended timeout for AI generation tests
  timeout: 90000, // 90 seconds per test (AI can be slow)
  expect: {
    timeout: 30000, // 30 seconds for expect() assertions
  },
  
  // Comprehensive reporting for AI validation
  reporter: [
    ['html', { 
      outputFolder: 'test-results/ai-validation-html-report',
      open: 'never' // Don't auto-open in CI
    }],
    ['json', { 
      outputFile: 'test-results/ai-validation-results.json' 
    }],
    ['junit', { 
      outputFile: 'test-results/ai-validation-junit.xml' 
    }],
    // Custom console reporter for AI validation
    ['line'],
    // List reporter for detailed output
    ['list']
  ],
  
  // Shared settings optimized for AI testing
  use: {
    // Base URL for Novel Engine frontend
    baseURL: 'http://localhost:5173',
    
    // Always collect trace for AI validation (for debugging)
    trace: 'on',
    
    // Always take screenshots for evidence
    screenshot: 'on',
    
    // Record video for all AI tests (evidence collection)
    video: 'on',
    
    // Browser context optimized for AI testing
    viewport: { width: 1920, height: 1080 }, // Large viewport for complex UIs
    ignoreHTTPSErrors: true,
    
    // Extended navigation timeout for AI-heavy pages
    navigationTimeout: 60000,
    
    // Extended action timeout for AI interactions
    actionTimeout: 30000,
    
    // HTTP headers for AI API testing
    extraHTTPHeaders: {
      'Accept': 'application/json, text/plain, */*',
      'Content-Type': 'application/json',
      'User-Agent': 'NovelEngine-AI-Validation-Tests/1.0'
    },
    
    // Locale for consistent testing
    locale: 'en-US',
    timezoneId: 'America/New_York',
    
    // Permissions for potential file uploads in AI testing
    permissions: ['camera', 'microphone'],
    
    // Color scheme for UI consistency
    colorScheme: 'light'
  },

  // Browser projects optimized for AI validation
  projects: [
    {
      name: 'chromium-ai-validation',
      use: { 
        ...devices['Desktop Chrome'],
        // Chrome-specific optimizations for AI testing
        launchOptions: {
          args: [
            '--disable-web-security', // For cross-origin AI API calls
            '--disable-features=TranslateUI', // Prevent translation interference
            '--no-first-run',
            '--disable-default-apps',
            '--disable-popup-blocking',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows'
          ],
          slowMo: 500 // Slow down for AI testing stability
        }
      },
    },
    
    // Firefox for AI validation (cross-browser testing)
    {
      name: 'firefox-ai-validation',
      use: { 
        ...devices['Desktop Firefox'],
        launchOptions: {
          firefoxUserPrefs: {
            'dom.webnotifications.enabled': false, // Prevent notification interruptions
            'dom.push.enabled': false,
            'media.navigator.permission.disabled': true,
            // Network optimizations for AI API calls
            'network.http.max-connections': 100,
            'network.http.max-connections-per-server': 10,
            'network.http.max-persistent-connections-per-server': 8
          }
        }
      },
    },

    // Mobile testing for AI generation
    {
      name: 'mobile-chrome-ai',
      use: { 
        ...devices['Pixel 5'],
        // Mobile-specific AI testing adjustments
        launchOptions: {
          args: [
            '--disable-web-security',
            '--disable-features=TranslateUI'
          ]
        }
      },
    }
  ],

  // Web server configuration for AI testing
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      stdout: 'ignore',
      stderr: 'pipe',
      timeout: 180000, // 3 minutes for server startup
      env: {
        NODE_ENV: 'test',
        VITE_HOST: '0.0.0.0',
        // Ensure AI testing mode is enabled
        VITE_AI_TESTING_MODE: 'true'
      }
    },
    // Optionally start API server if not running
    ...(process.env.AUTO_START_API ? [{
      command: 'python api_server.py',
      url: 'http://127.0.0.1:8003/health',
      reuseExistingServer: true,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 120000,
      env: {
        GEMINI_API_KEY: process.env.GEMINI_API_KEY || 'test-key-please-configure',
        NODE_ENV: 'test'
      }
    }] : [])
  ],

  // Global setup for AI validation testing
  globalSetup: './src/tests/ai-validation-global-setup.js',
  globalTeardown: './src/tests/ai-validation-global-teardown.js',

  // Output directory for all AI validation artifacts
  outputDir: 'test-results/ai-validation-artifacts/',
  
  // Preserve output for analysis
  preserveOutput: 'always', // Keep all AI test artifacts
  
  // Metadata for AI validation reporting
  metadata: {
    testSuite: 'Novel Engine AI Generation Validation',
    purpose: 'Validate real AI generation vs templates/state machines',
    framework: 'Playwright',
    aiProviders: ['Gemini 2.0 Flash', 'OpenAI GPT-4', 'Anthropic Claude'],
    testTypes: [
      'Creative Scenario Testing',
      'Template Pattern Detection',
      'Multi-Agent Coordination',
      'Content Quality Analysis',
      'Response Variation Analysis',
      'Real-time AI Processing',
      'Freedom/Flexibility Testing'
    ]
  }
});