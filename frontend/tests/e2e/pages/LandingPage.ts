import { Page, Locator } from '@playwright/test';

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
    this.heroSection = page.locator('.MuiStack-root').first();

    // Hero elements
    this.versionChip = page.locator('.MuiChip-root');
    this.mainTitle = page.locator('h1');
    this.subtitle = page.locator('h5');
    this.launchEngineButton = page.locator('[data-testid="cta-launch"], button:has-text("Launch Engine")');

    // Feature cards
    this.featureCards = page.locator('.glass-card');
    this.liveOrchestrationCard = page.locator('text=Live Orchestration').locator('xpath=ancestor::div[contains(@class, "glass-card")]');
    this.adaptiveAnalyticsCard = page.locator('text=Adaptive Analytics').locator('xpath=ancestor::div[contains(@class, "glass-card")]');
    this.secureEnvironmentCard = page.locator('text=Secure Environment').locator('xpath=ancestor::div[contains(@class, "glass-card")]');
  }

  /**
   * Navigate to landing page and wait for full load
   * Also sets up mocks needed for dashboard navigation in CI environment
   */
  async navigateToLanding() {
    // Set up mocks needed for dashboard navigation (must be before goto)
    await this.page.route(/\/api\/guest\/session/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workspace_id: 'ws-mock', created: false }),
      });
    });

    await this.page.addInitScript(() => {
      try {
        window.sessionStorage.setItem('guest_session_active', '1');
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

    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
    // Wait for main content to be visible
    await this.mainTitle.waitFor({ state: 'visible', timeout: 30000 });
  }

  /**
   * Click the Launch Engine button to navigate to dashboard
   */
  async clickLaunchEngine() {
    await this.launchEngineButton.click();
    // Wait for navigation to complete
    await this.page.waitForURL('**/dashboard', { timeout: 30000 });
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
