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

  // Skip verification if PLAYWRIGHT_SKIP_VERIFY is set (useful for WSL/CI environments)
  if (process.env.PLAYWRIGHT_SKIP_VERIFY === 'true') {
    console.log('ℹ️ Skipping dashboard verification (PLAYWRIGHT_SKIP_VERIFY=true)');
  } else {
    await verifyDashboardAccessibilityWithRetry(config.use?.baseURL || 'http://localhost:3000');
  }

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
async function verifyDashboardAccessibility(baseUrl: string) {
  console.log(`🌐 Verifying dashboard accessibility at ${baseUrl}...`);

  // Use curl for HTTP check (most reliable in WSL where Node.js fetch and Playwright browser can fail)
  try {
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    const { stdout } = await execAsync(`curl -s -o /dev/null -w "%{http_code}" "${baseUrl}"`, { timeout: 10000 });
    const statusCode = parseInt(stdout.trim(), 10);

    if (statusCode === 200) {
      console.log(`🌐 Dashboard HTTP check passed (status: ${statusCode})`);
      // In WSL or CI, skip browser verification since HTTP works but Playwright often can't connect
      if (process.env.WSL_DISTRO_NAME || process.env.WSLENV || process.env.CI) {
        console.log('ℹ️ WSL/CI detected - skipping browser verification');
        return;
      }
      // On other systems, still do browser verification for full confidence
      console.log('ℹ️ Proceeding with browser verification...');
    } else {
      console.log(`⚠️ HTTP check returned status ${statusCode}, trying browser check...`);
    }
  } catch (error) {
    console.log(`ℹ️ curl check failed (${error instanceof Error ? error.message : error}), trying browser check...`);
  }

  // Fall back to browser check
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

    const launchCta = page.locator('[data-testid="cta-launch"]');
    const guestChip = page.locator('[data-testid="guest-mode-chip"]');

    const ctaVisible = await launchCta
      .waitFor({ state: 'visible', timeout: 15000 })
      .then(() => true)
      .catch(() => false);

    if (ctaVisible) {
      console.log('🧪 Landing page detected; triggering Launch Engine CTA…');
      await launchCta.click();
    } else if (!(await guestChip.isVisible().catch(() => false))) {
      console.log('ℹ️ No landing CTA visible; assuming direct dashboard access.');
    }

    if (!page.url().includes('/dashboard')) {
      await page.waitForURL('**/dashboard', { timeout: 20000, waitUntil: 'domcontentloaded' });
    }
    await page.waitForSelector('[data-testid="dashboard-layout"]', { timeout: 30000, state: 'attached' });
    await page.waitForSelector('[data-testid="world-state-map"]', { timeout: 10000, state: 'attached' });
    await page.waitForSelector('[data-testid="system-log"]', { timeout: 10000, state: 'attached' });

    console.log('🌐 Dashboard accessibility verified');

  } catch (error) {
    console.error('❌ Dashboard accessibility check failed:', error);
    throw new Error('Dashboard not accessible - setup failed');

  } finally {
    await context.close();
    await browser.close();
  }
}

async function verifyDashboardAccessibilityWithRetry(baseUrl: string) {
  const attempts = Number(process.env.PLAYWRIGHT_VERIFY_ATTEMPTS ?? '3');
  const delayMs = Number(process.env.PLAYWRIGHT_VERIFY_RETRY_DELAY ?? '5000');
  let lastError: unknown = null;

  for (let i = 1; i <= attempts; i++) {
    try {
      await verifyDashboardAccessibility(baseUrl);
      return;
    } catch (error) {
      lastError = error;
      const remaining = attempts - i;
      console.warn(
        `⚠️ Dashboard verification attempt ${i}/${attempts} failed${remaining > 0 ? `; retrying in ${delayMs}ms...` : '.'
        }`,
        error,
      );
      if (remaining > 0) {
        await delay(delayMs);
      }
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error('Dashboard verification failed after retrying');
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export default globalSetup;
