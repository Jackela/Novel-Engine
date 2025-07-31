/**
 * Global Setup for Playwright Tests
 * 
 * This file runs once before all tests and handles:
 * - Environment preparation
 * - Global test data setup
 * - API server verification
 */

export default async function globalSetup() {
  console.log('🔧 Setting up test environment...');
  
  // Wait for web server to be fully ready
  const webServerUrl = 'http://localhost:5173';
  let retries = 30;
  let serverReady = false;
  
  console.log('⏳ Waiting for dev server to be ready...');
  while (retries > 0 && !serverReady) {
    try {
      const response = await fetch(webServerUrl);
      if (response.status === 200 || response.status === 404) {
        serverReady = true;
        console.log('✅ Dev server is ready');
      }
    } catch {
      retries--;
      if (retries > 0) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  }
  
  if (!serverReady) {
    throw new Error('Dev server failed to start properly');
  }
  
  // Verify API server is available (optional - tests will mock responses)
  try {
    const response = await fetch('http://localhost:8000/health');
    if (response.ok) {
      console.log('✅ API server is running and healthy');
    }
  } catch {
    console.log('⚠️  API server not running - tests will use mocked responses');
  }
  
  // Additional global setup can be added here
  // For example: database seeding, test user creation, etc.
  
  console.log('✅ Test environment setup complete');
}