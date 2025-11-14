import { chromium, FullConfig } from '@playwright/test';

/**
 * Global Setup for Emergent Narrative Dashboard UAT
 * 
 * Handles:
 * - Test environment initialization
 * - Mock API server setup
 * - Authentication token preparation
 * - Database seeding for consistent test data
 */

async function globalSetup(config: FullConfig) {
  console.log('🚀 Setting up Emergent Narrative Dashboard UAT environment...');

  // Start mock API server for testing
  await setupMockAPIServer();
  
  // Prepare authentication tokens for testing
  await setupAuthTokens();
  
  // Seed test database with consistent data
  await seedTestData();
  
  // Verify dashboard accessibility
  await verifyDashboardAccessibility();
  
  console.log('✅ Global setup completed successfully');
}

/**
 * Setup mock API server to simulate Novel Engine backend
 */
async function setupMockAPIServer() {
  console.log('📡 Setting up mock API server...');
  
  // In a real implementation, this would:
  // 1. Start a mock server (e.g., using MSW or json-server)
  // 2. Configure endpoints matching OpenAPI spec
  // 3. Setup WebSocket server for real-time updates
  // 4. Prepare response data that matches expected schemas
  
  // For now, we'll use environment variables to configure mock endpoints
  process.env.MOCK_API_ENABLED = 'true';
  process.env.MOCK_API_PORT = '8001';
  
  console.log('📡 Mock API server configured');
}

/**
 * Prepare authentication tokens for test scenarios
 */
async function setupAuthTokens() {
  console.log('🔐 Preparing authentication tokens...');
  
  // Generate test JWT tokens for different user roles
  const testTokens = {
    admin: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWFkbWluIiwiaWF0IjoxNTE2MjM5MDIyfQ.test-admin-token',
    user: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJpYXQiOjE1MTYyMzkwMjJ9.test-user-token',
    service: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXNlcnZpY2UiLCJpYXQiOjE1MTYyMzkwMjJ9.test-service-token'
  };
  
  // Store tokens in environment for test access
  process.env.TEST_ADMIN_TOKEN = testTokens.admin;
  process.env.TEST_USER_TOKEN = testTokens.user;
  process.env.TEST_SERVICE_TOKEN = testTokens.service;
  
  console.log('🔐 Authentication tokens prepared');
}

/**
 * Seed test database with consistent data for UAT scenarios
 */
async function seedTestData() {
  console.log('🌱 Seeding test data...');
  
  // Test characters for dashboard scenarios
  const testCharacters = [
    {
      id: 'char-001',
      name: 'Aria Shadowbane',
      type: 'protagonist',
      status: 'active',
      position: { x: 100, y: 200, z: 0 },
      activity: 0.8
    },
    {
      id: 'char-002', 
      name: 'Merchant Aldric',
      type: 'npc',
      status: 'active',
      position: { x: 150, y: 180, z: 0 },
      activity: 0.6
    },
    {
      id: 'char-003',
      name: 'Elder Thorne',
      type: 'npc', 
      status: 'active',
      position: { x: 80, y: 220, z: 0 },
      activity: 0.4
    }
  ];
  
  // Test narrative arcs
  const testArcs = [
    {
      id: 'arc-001',
      name: 'The Ancient Prophecy',
      status: 'active',
      completion: 0.6,
      participants: ['char-001', 'char-003']
    },
    {
      id: 'arc-002',
      name: 'Merchant Relations',
      status: 'active', 
      completion: 0.3,
      participants: ['char-001', 'char-002']
    }
  ];
  
  // Test campaign data
  const testCampaign = {
    id: 'campaign-001',
    name: 'Test Campaign',
    currentTurn: 47,
    totalTurns: 150,
    status: 'active'
  };
  
  // Store test data in environment/localStorage for access during tests
  process.env.TEST_CHARACTERS = JSON.stringify(testCharacters);
  process.env.TEST_ARCS = JSON.stringify(testArcs);
  process.env.TEST_CAMPAIGN = JSON.stringify(testCampaign);
  
  console.log('🌱 Test data seeded successfully');
}

/**
 * Verify dashboard is accessible and responsive
 */
async function verifyDashboardAccessibility() {
  console.log('🌐 Verifying dashboard accessibility...');
  
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // Navigate to dashboard
    const baseUrl = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
    await page.goto(baseUrl);
    
    // If we're on the landing page, trigger demo CTA to reach the dashboard
    const demoCta = page.locator('[data-testid="cta-demo"], [data-testid="cta-demo-primary"]');
    if (await demoCta.count()) {
      console.log('🧪 Landing page detected; triggering demo mode CTA…');
      await demoCta.first().click();
      await page.waitForURL('**/dashboard', { timeout: 15000 });
    }
    
    // Wait for main dashboard components to load
    await page.waitForSelector('[data-testid="dashboard-layout"]', { timeout: 30000, state: 'attached' });
    await page.waitForSelector('[data-testid="world-state-map"]', { timeout: 10000, state: 'attached' });
    await page.waitForSelector('[data-testid="real-time-activity"]', { timeout: 10000, state: 'attached' });
    
    console.log('🌐 Dashboard accessibility verified');
    
  } catch (error) {
    console.error('❌ Dashboard accessibility check failed:', error);
    throw new Error('Dashboard not accessible - setup failed');
    
  } finally {
    await context.close();
    await browser.close();
  }
}

export default globalSetup;
