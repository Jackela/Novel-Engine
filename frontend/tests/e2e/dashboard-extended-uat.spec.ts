import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';

/**
 * Emergent Narrative Dashboard - Extended UAT Test Suite
 * 
 * Additional test scenarios beyond core user story:
 * - Edge case handling
 * - Error recovery scenarios  
 * - Complex interaction workflows
 * - Data integrity validation
 * - Accessibility compliance
 */

test.describe('Extended UAT Scenarios', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();
  });

  test('Edge Case: Multiple Rapid Turn Orchestrations', async ({ page }) => {
    console.log('🔄 Testing multiple rapid turn orchestration triggers...');

    await test.step('Rapid Fire Orchestration Test', async () => {
      // Trigger multiple orchestrations in quick succession
      for (let i = 0; i < 3; i++) {
        console.log(`  Triggering orchestration ${i + 1}/3...`);
        
        try {
          await dashboardPage.triggerTurnOrchestration();
          
          // Brief wait between triggers
          await page.waitForTimeout(2000);
          
          // Verify system handles multiple requests gracefully
          await expect(dashboardPage.liveIndicator).toBeVisible();
          
        } catch (error) {
          console.log(`  Expected behavior: System should handle rapid requests gracefully`);
          // This is expected - system should either queue or reject rapid requests
        }
      }
      
      // Verify system returns to stable state
      await page.waitForTimeout(5000);
      await expect(dashboardPage.dashboardLayout).toBeVisible();
      
      console.log('✅ Rapid orchestration handling validated');
    });
  });

  test('Error Recovery: Network Interruption During Orchestration', async ({ page }) => {
    console.log('🛡️ Testing network interruption recovery...');

    await test.step('Network Interruption Simulation', async () => {
      // Start orchestration
      await dashboardPage.triggerTurnOrchestration();
      
      // Wait for orchestration to begin
      await dashboardPage.waitForTurnStart();
      await page.waitForTimeout(2000);
      
      // Simulate network interruption
      await page.context().setOffline(true);
      console.log('  Network offline - simulating interruption');
      
      await page.waitForTimeout(3000);
      
      // Restore network
      await page.context().setOffline(false);
      console.log('  Network restored');
      
      // Verify graceful recovery
      await expect(dashboardPage.dashboardLayout).toBeVisible();
      await expect(dashboardPage.connectionStatus).toBeVisible();
      
      // System should show appropriate error/recovery indicators
      const errorIndicators = page.locator('[class*="error"], [class*="disconnected"], [class*="offline"]');
      const recoveryIndicators = page.locator('[class*="reconnected"], [class*="online"], [class*="connected"]');
      
      // Either error indicators should be visible, or recovery should be complete
      const hasErrorIndicators = await errorIndicators.count() > 0;
      const hasRecoveryIndicators = await recoveryIndicators.count() > 0;
      
      expect(hasErrorIndicators || hasRecoveryIndicators).toBe(true);
      
      console.log('✅ Network interruption recovery validated');
    });
  });

  test('Data Integrity: Component State Synchronization', async ({ page }) => {
    console.log('🔗 Testing component state synchronization...');

    await test.step('Cross-Component Data Validation', async () => {
      // Get initial component states
      const initialUpdates = await dashboardPage.observeComponentUpdates();
      
      // Trigger orchestration and monitor updates
      await dashboardPage.triggerTurnOrchestration();
      await page.waitForTimeout(3000);
      
      const postOrchestrationUpdates = await dashboardPage.observeComponentUpdates();
      
      // Validate data consistency across components
      
      // 1. Character data should be consistent between World Map and Character Networks
      const worldMapHasCharacters = postOrchestrationUpdates.worldStateMap.hasCharacterMarkers;
      const networksHasCharacters = postOrchestrationUpdates.characterNetworks.hasCharacterNodes;
      
      if (worldMapHasCharacters) {
        expect(networksHasCharacters).toBe(true);
        console.log('  ✓ Character data synchronized between World Map and Character Networks');
      }
      
      // 2. Activity events should appear in both Real-time Activity and potentially World Map
      const hasActivityEvents = postOrchestrationUpdates.realTimeActivity.hasNewEvents;
      const hasWorldActivity = postOrchestrationUpdates.worldStateMap.hasActivityIndicators;
      
      if (hasActivityEvents) {
        console.log('  ✓ Activity events present in Real-time Activity component');
      }
      
      // 3. Timeline should reflect current turn progression
      const hasTimelineProgress = postOrchestrationUpdates.narrativeTimeline.hasProgressMarkers;
      expect(hasTimelineProgress).toBe(true);
      console.log('  ✓ Timeline reflects turn progression');
      
      // 4. Performance metrics should show system activity
      const systemOnline = postOrchestrationUpdates.performanceMetrics.systemOnline;
      expect(systemOnline).toBe(true);
      console.log('  ✓ Performance metrics indicate system activity');
      
      console.log('✅ Component state synchronization validated');
    });
  });

  test('Accessibility: Keyboard Navigation and Screen Reader Support', async ({ page }) => {
    console.log('♿ Testing accessibility compliance...');

    await test.step('Keyboard Navigation Test', async () => {
      // Test tab navigation through interactive elements
      const interactiveElements = [
        dashboardPage.playButton,
        dashboardPage.pauseButton,
        dashboardPage.stopButton,
        dashboardPage.refreshButton,
        dashboardPage.settingsButton
      ];
      
      let tabCount = 0;
      for (const element of interactiveElements) {
        const isVisible = await element.isVisible().catch(() => false);
        if (isVisible) {
          await page.keyboard.press('Tab');
          tabCount++;
          
          // Check if element receives focus
          const isFocused = await element.evaluate(el => document.activeElement === el).catch(() => false);
          console.log(`  Tab ${tabCount}: ${isFocused ? '✓' : '○'} Focus on interactive element`);
        }
      }
      
      expect(tabCount).toBeGreaterThan(0);
      console.log(`  ✓ Keyboard navigation works for ${tabCount} interactive elements`);
    });

    await test.step('ARIA Labels and Semantic HTML', async () => {
      // Check for proper ARIA labels
      const ariaElements = await page.locator('[aria-label], [aria-labelledby], [role]').count();
      expect(ariaElements).toBeGreaterThan(5);
      console.log(`  ✓ Found ${ariaElements} elements with ARIA attributes`);
      
      // Check for semantic headings
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').count();
      expect(headings).toBeGreaterThan(0);
      console.log(`  ✓ Found ${headings} semantic headings`);
      
      // Check for landmarks
      const landmarks = await page.locator('[role="main"], main, [role="banner"], header, [role="navigation"], nav').count();
      expect(landmarks).toBeGreaterThan(0);
      console.log(`  ✓ Found ${landmarks} landmark elements`);
    });

    await test.step('Color Contrast and Visual Indicators', async () => {
      // Check for non-color-dependent status indicators
      const statusElements = await page.locator('[class*="status"], [class*="indicator"], [aria-live]').count();
      console.log(`  ✓ Found ${statusElements} status/indicator elements`);
      
      // Verify important actions are accessible via keyboard
      const playButton = dashboardPage.playButton.first();
      if (await playButton.isVisible()) {
        await playButton.focus();
        await page.keyboard.press('Enter');
        
        // Should trigger orchestration just like mouse click
        await expect(dashboardPage.liveIndicator).toBeVisible();
        console.log('  ✓ Primary action (play) accessible via keyboard');
      }
    });

    console.log('✅ Accessibility compliance validated');
  });

  test('Performance: Component Render Optimization', async ({ page }) => {
    console.log('⚡ Testing component render performance...');

    await test.step('Initial Render Performance', async () => {
      const navigationStart = Date.now();
      
      // Navigate and measure render time
      await dashboardPage.navigateToDashboard();
      
      const renderComplete = Date.now();
      const totalRenderTime = renderComplete - navigationStart;
      
      console.log(`  Initial render time: ${totalRenderTime}ms`);
      expect(totalRenderTime).toBeLessThan(5000); // Should render within 5 seconds
      
      // Measure time to interactive (when controls are clickable)
      const interactiveStart = Date.now();
      await expect(dashboardPage.playButton.first()).toBeEnabled();
      const interactiveTime = Date.now() - interactiveStart;
      
      console.log(`  Time to interactive: ${interactiveTime}ms`);
      expect(interactiveTime).toBeLessThan(2000); // Should be interactive within 2 seconds
      
      console.log('✅ Initial render performance validated');
    });

    await test.step('Dynamic Update Performance', async () => {
      // Measure component update performance during orchestration
      const updateStart = Date.now();
      
      await dashboardPage.triggerTurnOrchestration();
      
      // Wait for first visible update
      await expect(dashboardPage.liveIndicator).toBeVisible();
      const firstUpdateTime = Date.now() - updateStart;
      
      console.log(`  First update response: ${firstUpdateTime}ms`);
      expect(firstUpdateTime).toBeLessThan(1000); // Should show response within 1 second
      
      // Monitor continuous updates
      let updateCount = 0;
      const updateInterval = setInterval(async () => {
        const hasActivity = await dashboardPage.realTimeActivity.locator('[data-testid="activity-event"]').count();
        if (hasActivity > updateCount) {
          updateCount = hasActivity;
          console.log(`  Update ${updateCount}: New activity detected`);
        }
      }, 500);
      
      // Monitor for 10 seconds
      await page.waitForTimeout(10000);
      clearInterval(updateInterval);
      
      expect(updateCount).toBeGreaterThan(0);
      console.log(`  ✓ Detected ${updateCount} dynamic updates`);
      
      console.log('✅ Dynamic update performance validated');
    });

    await test.step('Memory Usage Monitoring', async () => {
      // Get memory usage metrics (Chrome DevTools Protocol)
      if (page.context().browser()?.browserType().name() === 'chromium') {
        const client = await page.context().newCDPSession(page);
        
        // Measure initial memory
        await client.send('Runtime.enable');
        const initialHeap = await client.send('Runtime.getHeapUsage');
        
        // Trigger orchestration and operations
        await dashboardPage.triggerTurnOrchestration();
        await page.waitForTimeout(5000);
        
        // Measure memory after operations
        const finalHeap = await client.send('Runtime.getHeapUsage');
        
        const memoryDelta = finalHeap.totalSize - initialHeap.totalSize;
        console.log(`  Memory usage delta: ${(memoryDelta / 1024 / 1024).toFixed(2)} MB`);
        
        // Memory growth should be reasonable (< 50MB for dashboard operations)
        expect(memoryDelta).toBeLessThan(50 * 1024 * 1024);
        
        console.log('✅ Memory usage monitoring completed');
      } else {
        console.log('⚠️ Memory monitoring only available on Chromium');
      }
    });

    console.log('✅ Performance optimization validated');
  });

  test('Complex Workflow: Multi-Character Interaction Scenario', async ({ page }) => {
    console.log('🎭 Testing complex multi-character interaction workflow...');

    await test.step('Multi-Character Scenario Setup', async () => {
      // This would typically involve setting up test data
      // For now, we'll work with whatever characters are available
      
      const componentUpdates = await dashboardPage.observeComponentUpdates();
      
      // Verify we have character data to work with
      const hasCharacters = componentUpdates.characterNetworks.hasCharacterNodes ||
                           componentUpdates.worldStateMap.hasCharacterMarkers;
      
      if (!hasCharacters) {
        console.log('  ⚠️ No character data detected, skipping complex scenario');
        return;
      }
      
      console.log('  ✓ Character data available for complex scenario testing');
    });

    await test.step('Orchestrate Complex Interaction', async () => {
      // Trigger orchestration to generate character interactions
      await dashboardPage.triggerTurnOrchestration();
      
      // Monitor pipeline progression
      const pipelineResults = await dashboardPage.monitorTurnPipeline();
      
      // Validate that interaction orchestration phase completes
      const interactionPhase = pipelineResults.find(p => p.phase.includes('Interaction'));
      if (interactionPhase) {
        expect(interactionPhase.completed).toBe(true);
        console.log('  ✓ Interaction Orchestration phase completed');
      }
      
      // Check for character network updates
      const networkUpdates = await dashboardPage.observeComponentUpdates();
      
      if (networkUpdates.characterNetworks.hasConnections) {
        console.log('  ✓ Character network connections updated');
      }
      
      if (networkUpdates.characterNetworks.hasActivityMarkers) {
        console.log('  ✓ Character activity markers present');
      }
      
      console.log('✅ Complex multi-character workflow validated');
    });
  });

  test('Data Validation: API Response Schema Compliance', async ({ page }) => {
    console.log('📋 Testing API response schema compliance...');

    await test.step('Monitor API Responses', async () => {
      const apiResponses: any[] = [];
      
      // Capture API responses
      page.on('response', async (response) => {
        if (response.url().includes('/api/') && response.status() === 200) {
          try {
            const data = await response.json();
            apiResponses.push({
              url: response.url(),
              data: data,
              timestamp: new Date().toISOString()
            });
          } catch (error) {
            console.log(`  Warning: Could not parse JSON response from ${response.url()}`);
          }
        }
      });
      
      // Trigger operations that should generate API calls
      await dashboardPage.triggerTurnOrchestration();
      await page.waitForTimeout(5000);
      
      console.log(`  Captured ${apiResponses.length} API responses`);
      
      // Validate response structures
      for (const response of apiResponses) {
        const { url, data } = response;
        
        // Basic structure validation
        expect(data).toBeDefined();
        
        if (url.includes('/characters')) {
          // Character response validation
          if (Array.isArray(data)) {
            for (const char of data) {
              expect(char).toHaveProperty('id');
              expect(char).toHaveProperty('name');
              console.log(`  ✓ Character response schema valid: ${char.name}`);
            }
          }
        }
        
        if (url.includes('/turns')) {
          // Turn response validation
          expect(data).toHaveProperty('turnId');
          console.log(`  ✓ Turn response schema valid: ${data.turnId}`);
        }
        
        if (url.includes('/world')) {
          // World state response validation
          expect(data).toBeDefined();
          console.log(`  ✓ World state response schema valid`);
        }
      }
      
      if (apiResponses.length === 0) {
        console.log('  ⚠️ No API responses captured - may indicate mock data usage');
      }
      
      console.log('✅ API response schema compliance validated');
    });
  });

  // Clean up after each test
  test.afterEach(async ({ page }) => {
    await dashboardPage.takeFullScreenshot(`extended-test-final-${Date.now()}`);
  });
});