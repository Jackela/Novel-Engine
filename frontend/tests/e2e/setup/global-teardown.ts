import { FullConfig } from '@playwright/test';

/**
 * Global Teardown for Emergent Narrative Dashboard UAT
 * 
 * Handles:
 * - Test environment cleanup
 * - Mock server shutdown
 * - Test data cleanup
 * - Report generation preparation
 */

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Cleaning up Emergent Narrative Dashboard UAT environment...');

  // Cleanup mock API server
  await cleanupMockAPIServer();
  
  // Clear test data and tokens
  await clearTestData();
  
  // Generate test summary metrics
  await generateTestMetrics();
  
  console.log('✅ Global teardown completed successfully');
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
async function generateTestMetrics() {
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