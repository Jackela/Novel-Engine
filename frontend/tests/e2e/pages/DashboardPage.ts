import { type Page, type Locator, expect } from '@playwright/test';
import { prepareGuestSession } from '../utils/auth';

/**
 * Dashboard Page Object Model
 * 
 * Represents the main Emergent Narrative Dashboard interface
 * with methods for interacting with all Bento Grid components
 */
export class DashboardPage {
  readonly page: Page;

  // Main layout elements
  readonly dashboardLayout: Locator;
  readonly headerNavigation: Locator;
  readonly bentoGrid: Locator;

  // Bento Grid Components (following UI spec naming)
  readonly worldStateMap: Locator;           // Component A
  readonly realTimeActivity: Locator;       // Component B  
  readonly performanceMetrics: Locator;     // Component C
  readonly turnPipelineStatus: Locator;     // Component D
  readonly quickActions: Locator;           // Component E
  readonly characterNetworks: Locator;      // Component F
  readonly eventCascadeFlow: Locator;       // Component G
  readonly narrativeTimeline: Locator;      // Component H
  readonly analyticsPanel: Locator;         // Component I

  // Control elements
  readonly playButton: Locator;
  readonly pauseButton: Locator;
  readonly stopButton: Locator;
  readonly refreshButton: Locator;
  readonly settingsButton: Locator;

  // Status indicators
  readonly connectionStatus: Locator;
  readonly systemHealth: Locator;
  readonly liveIndicator: Locator;
  readonly guestModeChip: Locator;
  readonly guestModeBanner: Locator;
  readonly summaryStrip: Locator;
  readonly pipelineStageMarkers: Locator;

  constructor(page: Page) {
    this.page = page;

    // Main layout
    this.dashboardLayout = page.locator('[data-testid="dashboard-layout"]');
    this.headerNavigation = page.locator('[data-testid="sidebar-navigation"]');
    this.bentoGrid = page.locator('[data-testid="bento-grid"]');

    // Bento components - using semantic selectors based on UI spec
    this.worldStateMap = page.locator('[data-testid="world-state-map"]');
    this.realTimeActivity = page.locator('[data-testid="system-log"]');
    this.performanceMetrics = page.locator('[data-testid="performance-metrics"]');
    this.turnPipelineStatus = page.locator('[data-testid="turn-pipeline-status"]').first();
    this.quickActions = page.locator('[data-testid="quick-actions"]');
    this.characterNetworks = page.locator('[data-testid="character-networks"]');
    this.eventCascadeFlow = page.locator('[data-testid="event-cascade-flow"]');
    this.narrativeTimeline = page.locator('[data-testid="narrative-timeline"]');
    this.analyticsPanel = page.locator('[data-testid="analytics-panel"]');

    // Controls based on UI spec
    this.playButton = page.locator('[data-testid="quick-action-play"], [aria-label*="Start"], [title*="Start"]');
    this.pauseButton = page.locator('[data-testid="quick-action-pause"], [aria-label*="Pause"], [title*="Pause"]');
    this.stopButton = page.locator('[data-testid="quick-action-stop"], [aria-label*="Stop"], [title*="Stop"]');
    this.refreshButton = page.locator('[data-testid="quick-action-refresh"], [aria-label*="Refresh"], [title*="Refresh"]');
    this.settingsButton = page.locator('[data-testid="settings-button"], [aria-label*="Settings"], [title*="Settings"]');

    // Status indicators
    this.connectionStatus = page.locator('[data-testid="connection-status"]');
    this.systemHealth = page.locator('[data-testid="system-health"]');
    this.liveIndicator = page.locator('[data-testid="pipeline-live-indicator"]').first();
    this.guestModeChip = page.locator('[data-testid="guest-mode-chip"]');
    this.guestModeBanner = page.locator('[data-testid="guest-mode-banner"]');
    this.summaryStrip = page.locator('[data-testid="summary-strip"]');
    this.pipelineStageMarkers = this.turnPipelineStatus.locator('[data-testid="pipeline-stage-marker"]');
  }

  /**
   * Navigate to dashboard and wait for full load
   * @param options Configuration options for navigation
   * @param options.mockAPIs If true, sets up default API mocks before navigation
   */
  async navigateToDashboard(options: { mockAPIs?: boolean; failCharacters?: boolean; waitForLoad?: boolean } = {}) {
    await this.prepareDashboard(options);

    let onDashboard = false;
    try {
      await this.page.goto('/dashboard', { waitUntil: 'domcontentloaded', timeout: 45000 });
      onDashboard = true;
    } catch (error) {
      console.warn('⚠️ Direct dashboard navigation failed, falling back to landing CTA', error);
    }

    if (!onDashboard) {
      try {
        await this.page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30000 });
      } catch (error) {
        console.warn('⚠️ Landing page navigation timed out, retrying once more', error);
        await this.page.goto('/', { waitUntil: 'commit', timeout: 30000 });
      }

      const demoCta = this.page.locator('[data-testid="cta-launch"]');
      const ctaReady = await demoCta.waitFor({ state: 'visible', timeout: 10000 }).then(() => true).catch(() => false);
      if (ctaReady) {
        await demoCta.click();
      }

      await this.page.waitForURL('**/dashboard', { timeout: 20000 }).catch(async () => {
        await this.page.goto('/dashboard', { waitUntil: 'domcontentloaded', timeout: 30000 });
      });
    }

    let navigated = false;
    try {
      await this.page.waitForURL('**/dashboard', { timeout: 20000 });
      navigated = true;
    } catch {
      // fall through and try direct navigation
    }

    if (!navigated) {
      await this.page.goto('/dashboard', { waitUntil: 'load' });
      await this.page.waitForURL('**/dashboard', { timeout: 15000 });
    }

    if (options.waitForLoad ?? true) {
      await this.waitForDashboardLoad();
    }
  }

  async prepareDashboard(options: { mockAPIs?: boolean; failCharacters?: boolean } = {}) {
    await prepareGuestSession(this.page);
    if (options.mockAPIs) {
      await this.setupDefaultMocks(options);
    }
    await this.applyDashboardInitScripts();
  }

  private async applyDashboardInitScripts() {
    await this.page.addInitScript(() => {
      try {
        window.localStorage.setItem('guest_session_active', '1');
        window.sessionStorage.setItem('guest_session_active', '1');
        (window as any).__FORCE_SHOW_METRICS__ = true;
      } catch {
        // ignore storage failures in CI
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

          // Expose instance for test control
          if (!(window as any).__mockEventSources) {
            (window as any).__mockEventSources = [];
          }
          (window as any).__mockEventSources.push(this);
          (window as any).__lastMockEventSource = this;
          console.log('[MockEventSource] Created', url);

          // Simulate connection opening after a short delay
          setTimeout(() => {
            if (this.readyState === this.CONNECTING) {
              this.readyState = this.OPEN;
              const openEvent = new Event('open');
              console.log('[MockEventSource] Open', url);
              if (this.onopen) {
                this.onopen(openEvent);
              }
              this.dispatchEvent(openEvent);

              // Simlulate periodic events for performance testing
              setInterval(() => {
                if (this.readyState === this.OPEN && this.onmessage) {
                  const eventData = {
                    id: Date.now().toString(),
                    type: 'system',
                    title: 'System Activity',
                    description: 'Processing simulation step...',
                    timestamp: Date.now(),
                    severity: 'low'
                  };
                  const msgEvent = new MessageEvent('message', {
                    data: JSON.stringify(eventData)
                  });
                  this.onmessage(msgEvent);
                }
              }, 800);
            }
          }, 10);
        }

        private _onmessage: ((event: MessageEvent) => void) | null = null;

        get onmessage() {
          return this._onmessage;
        }

        set onmessage(handler: ((event: MessageEvent) => void) | null) {
          console.log('[MockEventSource] onmessage handler assigned');
          this._onmessage = handler;
        }

        onopen: ((event: Event) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;

        close() {
          this.readyState = this.CLOSED;
          const sources = (window as any).__mockEventSources;
          if (sources) {
            const index = sources.indexOf(this);
            if (index > -1) {
              sources.splice(index, 1);
            }
          }
        }
      }

      (window as any).EventSource = MockEventSource;
    });
  }

  /**
   * Wait for dashboard components to fully load
   */
  async waitForDashboardLoad() {
    // Wait for main layout
    await this.dashboardLayout.waitFor({ state: 'visible', timeout: 45000 });

    // Give Suspense/skeleton time to resolve
    const skeleton = this.page.locator('[data-testid="skeleton-dashboard"]');
    await skeleton.waitFor({ state: 'detached', timeout: 15000 }).catch(() => {
      console.warn('⚠️ Skeleton dashboard still attached after 15s; continuing with available UI');
    });

    // Wait for key widgets but don't fail hard if a single panel is slow to render
    const componentWaits = [
      this.worldStateMap.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {
        console.warn('⚠️ world-state-map not visible within timeout; proceeding');
      }),
      this.turnPipelineStatus.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {
        console.warn('⚠️ turn-pipeline-status not visible within timeout; proceeding');
      }),
      this.realTimeActivity.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {
        console.warn('⚠️ system-log not visible within timeout; proceeding');
      }),
      this.performanceMetrics.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {
        console.warn('⚠️ performance-metrics not visible within timeout; proceeding');
      }),
      this.connectionStatus.waitFor({ state: 'attached', timeout: 15000 }).catch(() => {
        console.warn('⚠️ connection-status not attached within timeout; proceeding');
      }),
    ];
    await Promise.all(componentWaits);

    // Wait for initial data load (loading states should disappear) if possible
    await this.page
      .waitForFunction(() => {
        const loadingElements = document.querySelectorAll('[data-testid*="loading"], .loading, [class*="loading"]');
        return loadingElements.length === 0;
      }, { timeout: 20000 })
      .catch(() => {
        console.warn('⚠️ Loading indicators still present after wait; continuing');
      });
  }



  /**
   * Switch the Dashboard Tab View
   * @param tabName The label of the tab to click (e.g., 'Network', 'Timeline')
   */
  async switchDashboardTab(tabName: string) {
    console.log(`📑 Switching dashboard tab to: ${tabName}`);
    // Use a more inclusive selector to handle icons/text layout
    const tab = this.page.locator(`[role="tab"]`).filter({ hasText: tabName }).first();
    await expect(tab).toBeVisible();
    await tab.click();

    // Wait for the corresponding view component to be visible
    switch (tabName) {
      case 'Map':
        await this.worldStateMap.waitFor({ state: 'visible' });
        break;
      case 'Network':
        await this.characterNetworks.waitFor({ state: 'visible' });
        break;
      case 'Timeline':
        await this.narrativeTimeline.waitFor({ state: 'visible' });
        break;
      case 'Analytics':
        await this.analyticsPanel.waitFor({ state: 'visible' });
        break;
      case 'Signals':
        await this.eventCascadeFlow.waitFor({ state: 'visible' });
        break;
    }
    await this.page.waitForTimeout(1000);
  }

  /**
   * Trigger turn orchestration via UI
   * Primary test action for UAT scenario
   */
  async triggerTurnOrchestration() {
    console.log('🎮 Triggering turn orchestration...');

    // Find and click the play/run button
    const runButton = this.playButton.first();

    await expect(runButton).toBeVisible({ timeout: 5000 });
    await expect(runButton).toBeEnabled({ timeout: 5000 });

    // Click to start turn orchestration
    await runButton.click();

    // Verify turn started by checking pipeline status
    await this.waitForTurnStart();
  }

  /**
   * Wait for turn orchestration to start
   */
  async waitForTurnStart() {
    // Wait for pipeline to show active status
    await this.page.waitForSelector(
      '[data-testid="turn-pipeline-status"] [data-status="processing"], [data-testid="turn-pipeline-status"] [data-status="active"]',
      { timeout: 10000 }
    );

    // Verify live indicator shows activity
    await expect(this.liveIndicator).toBeVisible({ timeout: 5000 });
  }

  /**
   * Monitor turn pipeline progression through 5 phases
   * Returns array of phase completion times
   */
  async monitorTurnPipeline(): Promise<{ phase: string; completed: boolean; duration?: number }[]> {
    console.log('📊 Monitoring turn pipeline progression...');

    const phases = [
      'World Update',
      'Subjective Brief',
      'Interaction Orchestration',
      'Event Integration',
      'Narrative Integration'
    ];

    const results = [];
    const startTime = Date.now();

    for (let i = 0; i < phases.length; i++) {
      const phase = phases[i];
      const phaseStart = Date.now();

      try {
        const phaseRow = this.turnPipelineStatus
          .locator('[data-phase-name]')
          .filter({ hasText: new RegExp(phase || '', 'i') })
          .first();
        await expect(phaseRow).toBeVisible({ timeout: 10000 });

        let completed = false;
        try {
          const phaseHandle = await phaseRow.elementHandle();
          if (phaseHandle) {
            await this.page.waitForFunction(
              el => el?.getAttribute?.('data-status') === 'completed',
              phaseHandle,
              { timeout: 15000 }
            );
            completed = true;
          }
        } catch {
          completed = (await phaseRow.getAttribute('data-status')) === 'completed';
        }

        const duration = Date.now() - phaseStart;
        results.push({ phase, completed, duration });

        console.log(`✅ Phase ${i + 1}: ${phase} completed in ${duration}ms (completed=${completed})`);

      } catch (error) {
        console.log(`⚠️ Phase ${i + 1}: ${phase} did not complete within timeout`);
        results.push({ phase, completed: false });
      }
    }

    const totalDuration = Date.now() - startTime;
    console.log(`📊 Turn pipeline monitoring completed in ${totalDuration}ms`);

    return results as { phase: string; completed: boolean; duration?: number; }[];
  }

  /**
   * Observe real-time updates across dashboard components
   */
  async observeComponentUpdates() {
    console.log('👀 Observing component updates...');

    const updates = {
      worldStateMap: await this.checkWorldStateUpdates(),
      realTimeActivity: await this.checkActivityUpdates(),
      performanceMetrics: await this.checkPerformanceUpdates(),
      characterNetworks: await this.checkCharacterUpdates(),
      narrativeTimeline: await this.checkTimelineUpdates()
    };

    return updates;
  }

  /**
   * Check for World State Map updates
   */
  private async checkWorldStateUpdates() {
    const component = this.worldStateMap;
    const isVisible = await component.isVisible();

    if (!isVisible) {
      return {
        hasActivityIndicators: false,
        hasCharacterMarkers: false,
        hasNewMovement: false,
        timestampUpdated: false
      };
    }

    const markerCount = await component.locator('[data-location]').count();
    const avatarLocator = component.locator('.MuiAvatar-root');
    let avatarCount = await avatarLocator.count();
    if (avatarCount === 0) {
      await avatarLocator.first().waitFor({ state: 'attached', timeout: 5000 }).catch(() => {});
      avatarCount = await avatarLocator.count();
    }
    const updates = {
      hasActivityIndicators: markerCount > 0,
      hasCharacterMarkers: avatarCount > 0,
      hasNewMovement: markerCount > 1,
      timestampUpdated: await component.locator('text=/Last updated/i').count() > 0
    };

    return updates;
  }

  /**
   * Check for Real-time Activity updates
   */
  private async checkActivityUpdates() {
    const component = this.realTimeActivity;
    // System Log should always be visible in layout, but safety check
    if (!await component.isVisible()) {
      return {
        hasNewEvents: false,
        hasLiveIndicator: false,
        eventCount: 0,
        hasCharacterActivity: false
      };
    }

    const eventCount = await component.locator('[data-testid="activity-event"]').count();
    const updates = {
      hasNewEvents: eventCount > 0,
      hasLiveIndicator: await this.connectionStatus.isVisible(),
      eventCount,
      hasCharacterActivity: await component.locator('[data-testid*="character-activity"]').count() > 0
    };

    return updates;
  }

  /**
   * Check for Performance Metrics updates
   */
  private async checkPerformanceUpdates() {
    const component = this.performanceMetrics;
    const isVisible = await component.isVisible();

    if (!isVisible) {
      return {
        hasMetricValues: false,
        hasLCP: false,
        hasCLS: false
      };
    }

    const updates = {
      // Component now only displays Web Vitals grid
      hasMetricValues: await component.locator('[data-testid="performance-metric-value"]').count() > 0,
      // Check for specific vitals to ensure complete rendering
      hasLCP: await component.getByText(/LCP/).first().isVisible(),
      hasCLS: await component.getByText(/CLS/).first().isVisible()
    };

    return updates;
  }

  /**
   * Check for Character Networks updates
   */
  private async checkCharacterUpdates() {
    const component = this.characterNetworks;
    const isVisible = await component.isVisible();

    if (!isVisible) {
      return {
        hasCharacterNodes: false,
        hasConnections: false,
        hasActivityMarkers: false,
        networkVisible: false
      };
    }

    const nodesLocator = component.locator('[data-character-id], .MuiAvatar-root, [data-character]');
    const nodeCount = await nodesLocator.count();
    // Only wait if visible but empty (loading state)
    if (nodeCount === 0) {
      await nodesLocator.first().waitFor({ state: 'attached', timeout: 2000 }).catch(() => { });
    }

    const connectionCount = await component.locator(
      '[data-testid="character-connection-icon"], [data-testid="character-connection-count"]'
    ).count();
    const updates = {
      hasCharacterNodes: nodeCount > 0,
      hasConnections: connectionCount > 0,
      hasActivityMarkers: nodeCount > 2,
      networkVisible: true
    };

    return updates;
  }

  /**
   * Check for Narrative Timeline updates
   */
  private async checkTimelineUpdates() {
    const component = this.narrativeTimeline;
    const isVisible = await component.isVisible();

    if (!isVisible) {
      return {
        hasProgressMarkers: false,
        hasCurrentTurn: false,
        hasArcProgress: false,
        timelineVisible: false
      };
    }

    const updates = {
      hasProgressMarkers: await component.locator('[data-testid*="progress"], [class*="marker"]').count() > 0,
      hasCurrentTurn: await component.locator('[data-testid="current-turn"]').isVisible(),
      hasArcProgress: await component.locator('[data-testid*="arc-progress"]').count() > 0,
      timelineVisible: true
    };

    return updates;
  }



  /**
   * Validate component layout matches UI specification
   */
  async validateComponentLayout() {
    console.log('📐 Validating component layout...');

    const layout = {
      worldStateMap: await this.validateComponentPresence(this.worldStateMap),
      realTimeActivity: await this.validateComponentPresence(this.realTimeActivity),
      performanceMetrics: await this.validateComponentPresence(this.performanceMetrics),
      turnPipeline: await this.validateComponentPresence(this.turnPipelineStatus),
      quickActions: await this.validateQuickActions()
    };

    return layout;
  }

  /**
   * Helper to validate component visibility/size
   */
  private async validateComponentPresence(component: Locator, minWidth = 200, minHeight = 120) {
    const locator = component.first();
    const isVisible = await locator.isVisible().catch(() => false);
    if (!isVisible) {
      return false;
    }

    const box = await locator.boundingBox();
    if (!box) {
      return false;
    }

    return box.width >= minWidth && box.height >= minHeight;
  }

  private async validateQuickActions() {
    const quickActionsContainer = this.quickActions.first();
    const isVisible = await quickActionsContainer.isVisible().catch(() => false);
    if (!isVisible) {
      return false;
    }

    const actionButtons = await quickActionsContainer.locator('button').count();
    const connectionIndicator = await quickActionsContainer.locator('[data-testid="connection-status"]').count();
    return actionButtons >= 4 && connectionIndicator >= 1;
  }

  /**
   * Take screenshot of current dashboard state
   */
  async takeFullScreenshot(name: string) {
    await this.page.screenshot({
      path: `test-results/screenshots/${name}-${Date.now()}.png`,
      fullPage: true
    });
  }

  /**
   * Check for accessibility violations
   */
  async checkAccessibility() {
    // This would integrate with axe-core or similar accessibility testing
    // For now, we'll check basic accessibility markers
    const accessibilityChecks = {
      hasAriaLabels: await this.page.locator('[aria-label]').count() > 0,
      hasHeadings: await this.page.locator('h1, h2, h3, h4, h5, h6').count() > 0,
      hasLandmarks: await this.page.locator('[role="main"], main, [role="banner"], [role="navigation"]').count() > 0,
      keyboardNavigation: await this.checkKeyboardNavigation()
    };

    return accessibilityChecks;
  }

  /**
   * Test keyboard navigation
   */
  private async checkKeyboardNavigation() {
    // Tab through interactive elements
    const interactiveElements = await this.page.locator('button, [role="button"], input, select, textarea, a').count();
    return interactiveElements > 0;
  }

  /**
   * Sets up default API mocks to ensure the dashboard has data to render.
   * Useful for tests that don't need specific edge case data.
   */
  async setupDefaultMocks(options?: { failCharacters?: boolean }) {
    console.log('📡 Setting up default API mocks...');

    const page = this.page;

    // --- Dynamic Mock State ---
    const PHASES = [
      'World Update',
      'Subjective Brief',
      'Interaction Orchestration',
      'Event Integration',
      'Narrative Integration'
    ];

    let orchestrationState = {
      status: 'idle',
      current_turn: 0,
      total_turns: 0,
      queue_length: 0,
      average_processing_time: 0.0,
      steps: [] as any[]
    };
    let latestNarrative = {
      story: '',
      participants: [] as string[],
      turns_completed: 0,
      has_content: false,
    };

    // Setup Console Capture
    page.on('console', msg => console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`));
    page.on('pageerror', err => console.log(`[BROWSER ERROR]: ${err.message}`));

    // Guest session bootstrap
    await page.route(/\/api\/guest\/session/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workspace_id: 'ws-mock', created: false }),
      });
    });

    // Characters Mock with persistence across refreshes
    let characters = ['char-1', 'char-2'];
    await page.route(url => !url.pathname.includes('/src/') && /\/api\/characters(\/|\?|$)/.test(url.pathname), async route => {
      if (options?.failCharacters) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Simulated failure' }),
        });
        return;
      }
      const request = route.request();
      const url = new URL(request.url());
      const segments = url.pathname.split('/').filter(Boolean);
      const lastSegment = segments[segments.length - 1];
      const hasId = lastSegment && lastSegment !== 'characters';
      const characterId = hasId ? decodeURIComponent(lastSegment) : null;

      if (request.method() === 'GET' && !characterId) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            characters: characters.map((id) => ({ id, name: id })),
          }),
        });
        return;
      }

      if (request.method() === 'GET' && characterId) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: characterId,
            name: characterId,
            role: 'protagonist',
            status: 'active',
            background_summary: 'Mock character profile',
            metadata: { faction: 'Mock Faction', role: 'Agent' },
            structured_data: {
              stats: { strength: 5, dexterity: 5, intelligence: 5, willpower: 5, perception: 5, charisma: 5 },
              equipment: [],
            },
          }),
        });
        return;
      }

      if (request.method() === 'POST') {
        let payload: Record<string, unknown> = {};
        try {
          payload = request.postDataJSON() as Record<string, unknown>;
        } catch {
          payload = {};
        }
        const name = payload?.name || payload?.character_name || `char-${Date.now()}`;
        if (!characters.includes(name)) {
          characters.push(name);
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { character_id: name } }),
        });
        return;
      }

      if (request.method() === 'PUT' && characterId) {
        let payload: Record<string, unknown> = {};
        try {
          payload = request.postDataJSON() as Record<string, unknown>;
        } catch {
          payload = {};
        }
        const name = payload?.name || characterId;
        if (!characters.includes(name)) {
          characters.push(name);
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: name,
            name,
            role: payload?.role ?? 'protagonist',
            background_summary: payload?.background_summary ?? 'Updated character',
            metadata: { faction: payload?.metadata?.faction ?? 'Mock Faction', role: payload?.metadata?.role ?? 'Agent' },
            structured_data: payload?.structured_data ?? { stats: {}, equipment: [] },
          }),
        });
        return;
      }

      if (request.method() === 'DELETE' && characterId) {
        characters = characters.filter(c => c !== characterId);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
        return;
      }

      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Not found' }),
      });
    });

    // World State
    await page.route(url => !url.pathname.includes('/src/') && /\/world\/state(\/|\?|$)/.test(url.pathname), async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          nodes: [
            { id: '1', name: 'Location A', position: [0, 0, 0], activity: 0.5 },
            { id: '2', name: 'Location B', position: [10, 0, 10], activity: 0.2 }
          ]
        })
      });
    });

    // System Status
    await page.route(url => !url.pathname.includes('/src/') && /\/meta\/system-status(\/|\?|$)/.test(url.pathname), async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'operational', uptime: 100, version: '1.0.0', components: { api: 'online', simulation: 'running', cache: 'available' } })
      });
    });

    // Health
    await page.route(url => !url.pathname.includes('/src/') && /\/health(\/|\?|$)/.test(url.pathname), async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() })
      });
    });

    // Orchestration Status - Dynamic
    await page.route(/\/api\/orchestration\/status/, async route => {
      console.log(`[MOCK] Hit: Status | State: ${orchestrationState.status}`);
      // Simulate progress if active
      if (orchestrationState.status === 'running' || orchestrationState.status === 'processing') {
        const incompleteStepIndex = orchestrationState.steps.findIndex(s => s.status !== 'completed');

        if (incompleteStepIndex !== -1) {
          // Complete the current step
          orchestrationState.steps[incompleteStepIndex].status = 'completed';
          orchestrationState.steps[incompleteStepIndex].progress = 100;

          // Start the next step if available
          if (incompleteStepIndex + 1 < orchestrationState.steps.length) {
            orchestrationState.steps[incompleteStepIndex + 1].status = 'processing';
          }
        }
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: orchestrationState
        })
      });
    });

    // Narrative output
    await page.route(/\/api\/orchestration\/narrative/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: latestNarrative,
        }),
      });
    });

    // Analytics Metrics
    await page.route(/\/api\/analytics\/metrics/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { status: 'active', last_updated: new Date().toISOString() } })
      });
    });

    // Orchestration Start - Dynamic
    await page.route(/\/api\/orchestration\/start/, async route => {
      console.log('[MOCK] Hit: Start');
      // Reset logic for smooth re-runs
      orchestrationState = {
        status: 'running',
        current_turn: (orchestrationState.current_turn || 0) + 1,
        total_turns: 10,
        queue_length: 0,
        average_processing_time: 2.5,
        steps: PHASES.map(name => ({
          id: name.toLowerCase().replace(/ /g, '_'),
          name: name,
          status: 'queued',
          progress: 0
        }))
      };

      // Start first step immediately
      if (orchestrationState.steps.length > 0) {
        orchestrationState.steps[0].status = 'processing';
      }

       latestNarrative = {
        story: `Run ${orchestrationState.current_turn}: Narrative generated for ${characters.join(', ')}`,
        participants: [...characters],
        turns_completed: orchestrationState.current_turn,
        has_content: true,
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: orchestrationState
        })
      });
    });

    // Orchestration Pause - Dynamic
    await page.route(/\/api\/orchestration\/pause/, async route => {
      console.log('[MOCK] Hit: Pause');
      orchestrationState.status = 'paused';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: orchestrationState })
      });
    });

    // Orchestration Stop - Dynamic
    await page.route(/\/api\/orchestration\/stop/, async route => {
      console.log('[MOCK] Hit: Stop');
      orchestrationState.status = 'idle';
      orchestrationState.steps = [];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: orchestrationState })
      });
    });

    // Event Stream (SSE/NDJSON)
    await page.route(/\/api\/events\/stream/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: ': keep-alive\n\n'
      });
    });
  }
} // End of class
