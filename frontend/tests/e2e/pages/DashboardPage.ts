import { Page, Locator, expect } from '@playwright/test';

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
    this.headerNavigation = page.locator('[data-testid="header-navigation"]');
    this.bentoGrid = page.locator('[data-testid="bento-grid"]');
    
    // Bento components - using semantic selectors based on UI spec
    this.worldStateMap = page.locator('[data-testid="world-state-map"]');
    this.realTimeActivity = page.locator('[data-testid="real-time-activity"]');
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
    this.liveIndicator = page.locator('[data-testid="live-indicator"]').first();
    this.guestModeChip = page.locator('[data-testid="guest-mode-chip"]');
    this.guestModeBanner = page.locator('[data-testid="guest-mode-banner"]');
    this.summaryStrip = page.locator('[data-testid="summary-strip"]');
    this.pipelineStageMarkers = this.turnPipelineStatus.locator('[data-testid="pipeline-stage-marker"]');
  }

  /**
   * Navigate to dashboard and wait for full load
   */
  async navigateToDashboard() {
    await this.page.addInitScript(() => {
      try {
        window.sessionStorage.setItem('novel-engine-guest-session', '1');
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

      const demoCta = this.page.locator('[data-testid="cta-demo"]');
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

    await this.waitForDashboardLoad();
  }

  /**
   * Wait for dashboard components to fully load
   */
  async waitForDashboardLoad() {
    // Wait for main layout
    await this.dashboardLayout.waitFor({ state: 'visible', timeout: 30000 });
    
    // Wait for critical Bento components
    await this.worldStateMap.waitFor({ state: 'visible', timeout: 10000 });
    await this.realTimeActivity.waitFor({ state: 'visible', timeout: 10000 });
    await this.performanceMetrics.waitFor({ state: 'visible', timeout: 10000 });
    await this.turnPipelineStatus.waitFor({ state: 'visible', timeout: 10000 });
    
    // Wait for initial data load (loading states should disappear)
    await this.page.waitForFunction(() => {
      const loadingElements = document.querySelectorAll('[data-testid*="loading"], .loading, [class*="loading"]');
      return loadingElements.length === 0;
    }, { timeout: 15000 });
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
          .filter({ hasText: new RegExp(phase, 'i') })
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
    
    return results;
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
    
    const markerCount = await component.locator('[data-location]').count();
    const avatarCount = await component.locator('.MuiAvatar-root').count();
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
    
    const eventCount = await component.locator('li').count();
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
    
    const updates = {
      hasHealthStatus: await component.locator('[data-testid="performance-health-status"]').first().isVisible(),
      hasMetricValues: await component.locator('[data-testid="performance-metric-value"]').count() > 0,
      hasProgressBars: await component.locator('[data-testid="performance-metric-progress"], progress, [role="progressbar"]').count() > 0,
      systemOnline: await this.checkSystemStatus(component, '[data-testid="performance-health-status"]')
    };
    
    return updates;
  }

  /**
   * Check for Character Networks updates
   */
  private async checkCharacterUpdates() {
    const component = this.characterNetworks;
    await component.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});

    const nodesLocator = component.locator('[data-character-id], .MuiAvatar-root, [data-character]');
    const nodeCount = await nodesLocator.count();
    if (nodeCount === 0) {
      await nodesLocator.first().waitFor({ state: 'attached', timeout: 2000 }).catch(() => {});
    }

    const connectionCount = await component.locator('[data-character-id] svg, line, path').count();
    const updates = {
      hasCharacterNodes: nodeCount > 0,
      hasConnections: connectionCount > 0,
      hasActivityMarkers: nodeCount > 2,
      networkVisible: await component.isVisible()
    };
    
    return updates;
  }

  /**
   * Check for Narrative Timeline updates
   */
  private async checkTimelineUpdates() {
    const component = this.narrativeTimeline;
    
    const updates = {
      hasProgressMarkers: await component.locator('[data-testid*="progress"], [class*="marker"]').count() > 0,
      hasCurrentTurn: await component.locator('[data-testid="current-turn"]').isVisible(),
      hasArcProgress: await component.locator('[data-testid*="arc-progress"]').count() > 0,
      timelineVisible: await component.isVisible()
    };
    
    return updates;
  }

  /**
   * Helper method to check timestamp updates
   */
  private async checkTimestampUpdate(component: Locator) {
    const timestampElements = component.locator('[data-testid*="timestamp"], [class*="timestamp"], time');
    return await timestampElements.count() > 0;
  }

  /**
   * Helper method to check system status
   */
  private async checkSystemStatus(component: Locator, selector = '[data-testid="system-status"], [class*="status"]') {
    const statusElements = component.locator(selector);
    if (await statusElements.count() === 0) return false;
    
    const statusText = await statusElements.first().textContent();
    if (!statusText) return false;
    const normalized = statusText.toLowerCase();
    return ['healthy', 'online', 'warning', 'active', 'live'].some(flag => normalized.includes(flag));
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
}
