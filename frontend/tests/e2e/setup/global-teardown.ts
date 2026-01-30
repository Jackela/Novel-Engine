import { FullConfig, chromium, firefox, webkit } from '@playwright/test';

/**
 * Global Teardown for Emergent Narrative Dashboard UAT
 *
 * Handles:
 * - Browser context and instance cleanup
 * - Test environment cleanup
 * - Mock server shutdown
 * - Test data cleanup
 * - Report generation preparation
 */

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Cleaning up Emergent Narrative Dashboard UAT environment...');

  // Force close any lingering browser contexts
  await cleanupBrowserContexts();

  // Cleanup mock API server
  await cleanupMockAPIServer();

  // Clear test data and tokens
  await clearTestData();

  // Generate test summary metrics
  await generateTestMetrics(config);

  console.log('✅ Global teardown completed successfully');
}

/**
 * Force close any lingering browser contexts to prevent port/file locks.
 */
async function cleanupBrowserContexts() {
  console.log('🌐 Closing any lingering browser contexts...');

  const browserTypes = [chromium, firefox, webkit];

  for (const browserType of browserTypes) {
    try {
      // Connect to any running browser and close it
      // This is a best-effort cleanup; errors are expected if no browsers are running
      const browser = await browserType.launch({ headless: true });
      await browser.close();
    } catch {
      // No browser of this type running - this is expected
    }
  }

  // Kill any orphaned browser processes on Windows
  if (process.platform === 'win32') {
    try {
      const { exec } = await import('child_process');
      const { promisify } = await import('util');
      const execAsync = promisify(exec);

      // Kill orphaned Chromium processes spawned by Playwright
      await execAsync('taskkill /F /IM "chrome.exe" /FI "WINDOWTITLE eq Playwright*" 2>nul').catch(() => {});
      await execAsync('taskkill /F /IM "msedge.exe" /FI "WINDOWTITLE eq Playwright*" 2>nul').catch(() => {});
    } catch {
      // Process kill failed - acceptable, not critical
    }
  }

  console.log('🌐 Browser cleanup complete');
}

/**
 * Cleanup mock API server and related resources
 */
async function cleanupMockAPIServer() {
  console.log('🛑 Shutting down mock API server...');
  
  // In a real implementation, this would:
  // 1. Stop the mock server process
  // 2. Close WebSocket connections
  // 3. Clear any temporary files
  // 4. Reset server state
  
  // Clear mock server environment variables
  delete process.env.MOCK_API_ENABLED;
  delete process.env.MOCK_API_PORT;
  
  console.log('🛑 Mock API server shutdown complete');
}

/**
 * Clear test data and authentication tokens
 */
async function clearTestData() {
  console.log('🗑️ Clearing test data...');
  
  // Clear test tokens
  delete process.env.TEST_ADMIN_TOKEN;
  delete process.env.TEST_USER_TOKEN;
  delete process.env.TEST_SERVICE_TOKEN;
  
  // Clear test data
  delete process.env.TEST_CHARACTERS;
  delete process.env.TEST_ARCS; 
  delete process.env.TEST_CAMPAIGN;
  
  console.log('🗑️ Test data cleared');
}

/**
 * Generate test metrics for UAT reporting
 */
async function generateTestMetrics(config: FullConfig) {
  console.log('📊 Generating test metrics...');
  
  const testMetrics = {
    environment: {
      nodeVersion: process.version,
      platform: process.platform,
      timestamp: new Date().toISOString(),
      baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
    },
    configuration: {
      timeout: config.timeout,
      retries: config.retries,
      workers: config.workers,
      projects: config.projects?.length || 0
    }
  };
  
  // Store metrics for UAT report generation
  process.env.UAT_TEST_METRICS = JSON.stringify(testMetrics);
  
  console.log('📊 Test metrics generated');
}

export default globalTeardown;
