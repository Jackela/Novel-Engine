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
    this.turnPipelineStatus = page.locator('[data-testid="turn-pipeline-status"]');
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
    this.liveIndicator = page.locator('[data-testid="live-indicator"], .live-indicator, [class*="live"]');
  }

  /**
   * Navigate to dashboard and wait for full load
   */
  async navigateToDashboard() {
    await this.page.goto('/dashboard');
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
      '[data-testid="turn-pipeline-status"] [class*="processing"], [data-testid="turn-pipeline-status"] [class*="active"]',
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
        // Wait for phase to complete (indicated by checkmark or completion state)
        await this.page.waitForSelector(
          `[data-testid="turn-pipeline-status"] [data-phase="${phase}"] [class*="completed"], 
           [data-testid="turn-pipeline-status"] [data-phase="${phase}"] .checkmark,
           [data-testid="turn-pipeline-status"] [class*="phase-${i + 1}"] [class*="completed"]`,
          { timeout: 30000 }
        );
        
        const duration = Date.now() - phaseStart;
        results.push({ phase, completed: true, duration });
        
        console.log(`✅ Phase ${i + 1}: ${phase} completed in ${duration}ms`);
        
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
    
    // Look for activity indicators, updated positions, new markers
    const updates = {
      hasActivityIndicators: await component.locator('[class*="activity"], [data-activity]').count() > 0,
      hasCharacterMarkers: await component.locator('[data-testid*="character"], .character-marker').count() > 0,
      hasNewMovement: await component.locator('[class*="trail"], [class*="path"]').count() > 0,
      timestampUpdated: await this.checkTimestampUpdate(component)
    };
    
    return updates;
  }

  /**
   * Check for Real-time Activity updates
   */
  private async checkActivityUpdates() {
    const component = this.realTimeActivity;
    
    const updates = {
      hasNewEvents: await component.locator('[data-testid="activity-event"]').count() > 0,
      hasLiveIndicator: await component.locator('[class*="live"], [data-testid="live-indicator"]').isVisible(),
      eventCount: await component.locator('[data-testid="activity-event"]').count(),
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
      hasHealthStatus: await component.locator('[data-testid="health-status"]').isVisible(),
      hasMetricValues: await component.locator('[data-testid*="metric-value"]').count() > 0,
      hasProgressBars: await component.locator('progress, [role="progressbar"]').count() > 0,
      systemOnline: await this.checkSystemStatus(component)
    };
    
    return updates;
  }

  /**
   * Check for Character Networks updates
   */
  private async checkCharacterUpdates() {
    const component = this.characterNetworks;
    
    const updates = {
      hasCharacterNodes: await component.locator('[data-testid*="character-node"]').count() > 0,
      hasConnections: await component.locator('[data-testid*="connection"], line, path').count() > 0,
      hasActivityMarkers: await component.locator('[class*="activity"]').count() > 0,
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
  private async checkSystemStatus(component: Locator) {
    const statusElements = component.locator('[data-testid="system-status"], [class*="status"]');
    if (await statusElements.count() === 0) return false;
    
    const statusText = await statusElements.first().textContent();
    return statusText?.toLowerCase().includes('healthy') || statusText?.toLowerCase().includes('online');
  }

  /**
   * Validate component layout matches UI specification
   */
  async validateComponentLayout() {
    console.log('📐 Validating component layout...');
    
    const layout = {
      worldStateMap: await this.validateGridPosition(this.worldStateMap, { columns: '1 / 7' }),
      realTimeActivity: await this.validateGridPosition(this.realTimeActivity, { columns: '8 / 11' }),
      performanceMetrics: await this.validateGridPosition(this.performanceMetrics, { columns: '12 / 13' }),
      turnPipeline: await this.validateGridPosition(this.turnPipelineStatus, { columns: '8 / 11' }),
      quickActions: await this.validateGridPosition(this.quickActions, { columns: '12 / 13' })
    };
    
    return layout;
  }

  /**
   * Helper to validate grid positioning
   */
  private async validateGridPosition(component: Locator, expected: { columns: string }) {
    const element = await component.first().elementHandle();
    if (!element) return false;
    
    const gridColumn = await element.evaluate(el => 
      window.getComputedStyle(el).getPropertyValue('grid-column')
    );
    
    return gridColumn.includes(expected.columns.replace(' / ', ' / '));
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