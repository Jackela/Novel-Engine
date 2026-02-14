import { Page, Locator } from '@playwright/test';
import { safeGoto } from '../utils/navigation';

/**
 * Landing Page Object Model
 *
 * Represents the Novel Engine landing page interface
 * with methods for interacting with all landing page elements
 */
export class LandingPage {
  readonly page: Page;

  // Main layout elements
  readonly mainContent: Locator;
  readonly heroSection: Locator;

  // Hero elements
  readonly versionChip: Locator;
  readonly mainTitle: Locator;
  readonly subtitle: Locator;
  readonly launchEngineButton: Locator;

  // Feature cards
  readonly featureCards: Locator;
  readonly liveOrchestrationCard: Locator;
  readonly adaptiveAnalyticsCard: Locator;
  readonly secureEnvironmentCard: Locator;

  constructor(page: Page) {
    this.page = page;

    // Main layout
    this.mainContent = page.locator('#main-content, [id="main-content"], main');
    this.heroSection = page.locator('main');

    // Hero elements
    this.versionChip = page.locator('[data-testid="version-chip"]');
    this.mainTitle = page.locator('h1');
    this.subtitle = page.locator('h5');
    this.launchEngineButton = page.locator('[data-testid="cta-launch"], button:has-text("Launch Engine")');

    // Feature cards
    this.featureCards = page.locator('[data-testid="feature-card"]');
    this.liveOrchestrationCard = this.featureCards.filter({ hasText: 'Live Orchestration' });
    this.adaptiveAnalyticsCard = this.featureCards.filter({ hasText: 'Adaptive Analytics' });
    this.secureEnvironmentCard = this.featureCards.filter({ hasText: 'Secure Environment' });
  }

  /**
   * Navigate to landing page and wait for full load
   * Also sets up mocks needed for dashboard navigation in CI environment
   */
  async navigateToLanding(options: { timeoutMs?: number } = {}) {
    const timeoutMs = options.timeoutMs ?? 45000;
    // Set up mocks needed for dashboard navigation (must be before goto)
    await this.page.route(/\/api\/guest\/sessions/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workspace_id: 'ws-mock', created: false }),
      });
    });

    await this.page.addInitScript(() => {
      try {
        const preserveAuth = window.localStorage.getItem('e2e_preserve_auth') === '1';
        if (!preserveAuth) {
          window.localStorage.removeItem('novel-engine-auth');
          window.localStorage.removeItem('novelengine_guest_session');
          window.sessionStorage.removeItem('novelengine_guest_session');
          window.localStorage.setItem('e2e_bypass_auth', '0');
          window.localStorage.removeItem('e2e_preserve_auth');
        }
      } catch {
        // ignore storage failures
      }

      // Mock EventSource for SSE testing
      class MockEventSource extends EventTarget {
        url: string;
        readyState: number = 0;
        CONNECTING = 0;
        OPEN = 1;
        CLOSED = 2;

        constructor(url: string) {
          super();
          this.url = url;
          this.readyState = this.CONNECTING;

          // Simulate connection opening after a short delay
          setTimeout(() => {
            if (this.readyState === this.CONNECTING) {
              this.readyState = this.OPEN;
              const openEvent = new Event('open');
              if (this.onopen) {
                this.onopen(openEvent);
              }
              this.dispatchEvent(openEvent);
            }
          }, 10);
        }

        onopen: ((event: Event) => void) | null = null;
        onmessage: ((event: MessageEvent) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;

        close() {
          this.readyState = this.CLOSED;
        }
      }

      (window as any).EventSource = MockEventSource;
    });

    await safeGoto(this.page, '/', { timeout: timeoutMs });
    // Wait for main content to be visible
    await Promise.race([
      this.mainTitle.waitFor({ state: 'visible', timeout: timeoutMs }),
      this.launchEngineButton.waitFor({ state: 'visible', timeout: timeoutMs }),
    ]);
  }

  /**
   * Click the Launch Engine button to navigate to dashboard
   */
  async clickLaunchEngine() {
    await this.launchEngineButton.click();
    // Wait for navigation to complete (URL or dashboard shell)
    await Promise.race([
      this.page.waitForURL('**/dashboard', { timeout: 30000, waitUntil: 'domcontentloaded' }),
      this.page.locator('[data-testid="dashboard-layout"]').waitFor({
        state: 'visible',
        timeout: 30000,
      }),
    ]);
    await this.page.evaluate(() => {
      try {
        window.localStorage.setItem('e2e_preserve_auth', '1');
      } catch {
        // ignore storage failures
      }
    });
  }

  /**
   * Get the main title text
   */
  async getMainTitleText(): Promise<string> {
    return await this.mainTitle.textContent() || '';
  }

  /**
   * Get the version chip text
   */
  async getVersionText(): Promise<string> {
    return await this.versionChip.textContent() || '';
  }

  /**
   * Get the number of feature cards
   */
  async getFeatureCardCount(): Promise<number> {
    return await this.featureCards.count();
  }

  /**
   * Take a screenshot of the landing page
   */
  async takeScreenshot(name: string) {
    await this.page.screenshot({
      path: `test-results/screenshots/${name}.png`,
      fullPage: true
    });
  }

  /**
   * Validate responsive layout at current viewport
   */
  async validateResponsiveLayout(): Promise<{
    titleVisible: boolean;
    buttonVisible: boolean;
    cardsVisible: boolean;
    layoutStacked: boolean;
  }> {
    const titleVisible = await this.mainTitle.isVisible();
    const buttonVisible = await this.launchEngineButton.isVisible();
    const cardsVisible = (await this.featureCards.count()) > 0;

    // Check if layout is stacked (mobile view) by checking grid column count
    const viewport = this.page.viewportSize();
    const layoutStacked = viewport ? viewport.width < 768 : false;

    return {
      titleVisible,
      buttonVisible,
      cardsVisible,
      layoutStacked
    };
  }
}
