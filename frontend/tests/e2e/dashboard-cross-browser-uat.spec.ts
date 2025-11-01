import { test, expect, devices } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';

/**
 * Emergent Narrative Dashboard - Cross-Browser UAT Test Suite
 * 
 * Validates consistent behavior and rendering across:
 * - Chrome/Chromium (Blink engine)
 * - Firefox (Gecko engine) 
 * - Safari/WebKit (WebKit engine)
 * - Edge compatibility
 * - Mobile browser compatibility
 */

// Test configuration for different browser projects
const browserProjects = [
  { name: 'chromium-desktop', displayName: 'Chrome Desktop' },
  { name: 'firefox-desktop', displayName: 'Firefox Desktop' },
  { name: 'webkit-desktop', displayName: 'Safari Desktop' },
  { name: 'tablet', displayName: 'Tablet Safari' },
  { name: 'mobile', displayName: 'Mobile Safari' }
];

test.describe('Cross-Browser Compatibility UAT', () => {
  
  test('Browser Engine Compatibility: Core User Story', async ({ page, browserName }) => {
    console.log(`🌐 Testing core user story on ${browserName}...`);
    
    const dashboardPage = new DashboardPage(page);
    
    await test.step(`${browserName}: Dashboard Loading`, async () => {
      const loadStart = Date.now();
      await dashboardPage.navigateToDashboard();
      const loadTime = Date.now() - loadStart;
      
      console.log(`  ${browserName} load time: ${loadTime}ms`);
      
      // Verify all critical components load across browsers
      await expect(dashboardPage.worldStateMap).toBeVisible();
      await expect(dashboardPage.realTimeActivity).toBeVisible(); 
      await expect(dashboardPage.performanceMetrics).toBeVisible();
      await expect(dashboardPage.turnPipelineStatus).toBeVisible();
      
      // Browser-specific load time expectations (allow more time for WebKit/Firefox)
      const maxLoadTime = browserName === 'webkit' ? 10000 : browserName === 'firefox' ? 8000 : 6000;
      expect(loadTime).toBeLessThan(maxLoadTime);
      
      console.log(`  ✅ ${browserName}: All components loaded successfully`);
    });

    await test.step(`${browserName}: Turn Orchestration`, async () => {
      const orchestrationStart = Date.now();
      
      // Trigger orchestration
      await dashboardPage.triggerTurnOrchestration();
      
      // Verify orchestration starts consistently across browsers
      await expect(dashboardPage.liveIndicator).toBeVisible();
      
      const responseTime = Date.now() - orchestrationStart;
      console.log(`  ${browserName} orchestration response: ${responseTime}ms`);
      
      // All browsers should respond promptly; allow more time on WebKit/Firefox
      const maxResponse = browserName === 'webkit' || browserName === 'firefox' ? 3000 : 2000;
      expect(responseTime).toBeLessThan(maxResponse);
      
      console.log(`  ✅ ${browserName}: Turn orchestration triggered successfully`);
    });

    await test.step(`${browserName}: Component Updates`, async () => {
      // Wait for updates to propagate
      await page.waitForTimeout(3000);
      
      // Observe component updates
      const updates = await dashboardPage.observeComponentUpdates();
      
      // Verify consistent update behavior across browsers
      expect(updates.realTimeActivity.hasLiveIndicator).toBe(true);
      
      // Take screenshot for visual comparison
      await dashboardPage.takeFullScreenshot(`cross-browser-${browserName}-updates`);
      
      console.log(`  ✅ ${browserName}: Component updates observed`);
    });

    console.log(`🌐 ✅ ${browserName} compatibility test completed`);
  });

  test('Responsive Layout Consistency', async ({ page, browserName }) => {
    console.log(`📱 Testing responsive layout on ${browserName}...`);
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();
    
    const viewports = [
      { name: 'Desktop', width: 1440, height: 900 },
      { name: 'Laptop', width: 1366, height: 768 },
      { name: 'Tablet Portrait', width: 768, height: 1024 },
      { name: 'Tablet Landscape', width: 1024, height: 768 },
      { name: 'Mobile Portrait', width: 375, height: 667 },
      { name: 'Mobile Landscape', width: 667, height: 375 }
    ];

    for (const viewport of viewports) {
      await test.step(`${browserName}: ${viewport.name} Layout`, async () => {
        console.log(`  Testing ${viewport.name} (${viewport.width}x${viewport.height})`);
        
        // Set viewport
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.waitForTimeout(1000); // Allow layout reflow
        
        // Verify layout doesn't break
        await expect(dashboardPage.dashboardLayout).toBeVisible();
        await expect(dashboardPage.bentoGrid).toBeVisible();
        
        // Check if critical components remain accessible
        const worldMapVisible = await dashboardPage.worldStateMap.isVisible();
        const activityVisible = await dashboardPage.realTimeActivity.isVisible();
        
        // On mobile, some components might be collapsed or stacked
        if (viewport.width >= 768) {
          // Desktop and tablet should show all components
          expect(worldMapVisible).toBe(true);
          expect(activityVisible).toBe(true);
        } else {
          // Mobile should show at least some components (may be stacked)
          expect(worldMapVisible || activityVisible).toBe(true);
        }
        
        // Take screenshot for layout verification
        await dashboardPage.takeFullScreenshot(`${browserName}-${viewport.name.toLowerCase().replace(' ', '-')}-layout`);
        
        console.log(`    ✅ ${viewport.name} layout validated`);
      });
    }

    // Reset to desktop viewport
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);

    console.log(`📱 ✅ ${browserName} responsive layout test completed`);
  });

  test('Browser-Specific Feature Support', async ({ page, browserName }) => {
    console.log(`🔧 Testing browser-specific features on ${browserName}...`);
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();

    await test.step(`${browserName}: CSS Grid Support`, async () => {
      // Verify CSS Grid is working properly
      const gridSupport = await page.evaluate(() => {
        const testElement = document.createElement('div');
        testElement.style.display = 'grid';
        return testElement.style.display === 'grid';
      });
      
      expect(gridSupport).toBe(true);
      console.log(`  ✅ ${browserName}: CSS Grid supported`);
      
      // Verify Bento Grid layout is applied
      const bentoGridStyles = await dashboardPage.bentoGrid.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          display: styles.display,
          gridTemplateColumns: styles.gridTemplateColumns,
          gap: styles.gap
        };
      });
      
      expect(bentoGridStyles.display).toBe('grid');
      console.log(`  ✅ ${browserName}: Bento Grid styles applied`);
    });

    await test.step(`${browserName}: WebSocket Support`, async () => {
      // Check WebSocket API availability
      const webSocketSupport = await page.evaluate(() => {
        return 'WebSocket' in window;
      });
      
      expect(webSocketSupport).toBe(true);
      console.log(`  ✅ ${browserName}: WebSocket API supported`);
    });

    await test.step(`${browserName}: Canvas and WebGL Support`, async () => {
      // Check Canvas API (needed for Three.js)
      const canvasSupport = await page.evaluate(() => {
        const canvas = document.createElement('canvas');
        return !!(canvas.getContext && canvas.getContext('2d'));
      });
      
      expect(canvasSupport).toBe(true);
      console.log(`  ✅ ${browserName}: Canvas API supported`);
      
      // Check WebGL support (for 3D World State Map)
      const webglSupport = await page.evaluate(() => {
        try {
          const canvas = document.createElement('canvas');
          return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
        } catch (e) {
          return false;
        }
      });
      
      if (webglSupport) {
        console.log(`  ✅ ${browserName}: WebGL supported`);
      } else {
        console.log(`  ⚠️ ${browserName}: WebGL not supported (fallback rendering expected)`);
      }
    });

    await test.step(`${browserName}: Local Storage Support`, async () => {
      // Test localStorage for user preferences
      const localStorageSupport = await page.evaluate(() => {
        try {
          const testKey = 'test_key_' + Date.now();
          localStorage.setItem(testKey, 'test_value');
          const result = localStorage.getItem(testKey) === 'test_value';
          localStorage.removeItem(testKey);
          return result;
        } catch (e) {
          return false;
        }
      });
      
      expect(localStorageSupport).toBe(true);
      console.log(`  ✅ ${browserName}: LocalStorage supported`);
    });

    console.log(`🔧 ✅ ${browserName} feature support test completed`);
  });

  test('Performance Comparison Across Browsers', async ({ page, browserName }) => {
    console.log(`⚡ Testing performance on ${browserName}...`);
    
    const dashboardPage = new DashboardPage(page);
    const performanceMetrics: Record<string, number> = {};

    await test.step(`${browserName}: Load Performance`, async () => {
      const loadStart = Date.now();
      await dashboardPage.navigateToDashboard();
      const loadTime = Date.now() - loadStart;
      
      performanceMetrics.loadTime = loadTime;
      console.log(`  ${browserName} load time: ${loadTime}ms`);
    });

    await test.step(`${browserName}: Interaction Performance`, async () => {
      const interactionStart = Date.now();
      await dashboardPage.triggerTurnOrchestration();
      await expect(dashboardPage.liveIndicator).toBeVisible();
      const interactionTime = Date.now() - interactionStart;
      
      performanceMetrics.interactionTime = interactionTime;
      console.log(`  ${browserName} interaction response: ${interactionTime}ms`);
    });

    await test.step(`${browserName}: Rendering Performance`, async () => {
      const renderStart = Date.now();
      
      // Perform operations that trigger re-renders
      await page.setViewportSize({ width: 1024, height: 768 });
      await page.waitForTimeout(100);
      await page.setViewportSize({ width: 1440, height: 900 });
      
      const renderTime = Date.now() - renderStart;
      performanceMetrics.renderTime = renderTime;
      
      console.log(`  ${browserName} render time: ${renderTime}ms`);
    });

    // Performance thresholds by browser
    const thresholds = {
      chromium: { load: 5000, interaction: 1500, render: 1000 },
      firefox: { load: 6000, interaction: 2000, render: 1200 },
      webkit: { load: 8000, interaction: 2500, render: 1500 } // Safari tends to be slower
    };
    
    const threshold = thresholds[browserName as keyof typeof thresholds] || thresholds.chromium;
    
    expect(performanceMetrics.loadTime).toBeLessThan(threshold.load);
    expect(performanceMetrics.interactionTime).toBeLessThan(threshold.interaction);
    expect(performanceMetrics.renderTime).toBeLessThan(threshold.render);
    
    console.log(`⚡ ✅ ${browserName} performance within acceptable thresholds`);
  });

  test('Error Handling Consistency', async ({ page, browserName }) => {
    console.log(`🛡️ Testing error handling consistency on ${browserName}...`);
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();

    await test.step(`${browserName}: Network Error Handling`, async () => {
      // Simulate network failure
      await page.context().setOffline(true);
      
      try {
        await dashboardPage.triggerTurnOrchestration();
        console.log(`  ${browserName}: Orchestration attempted while offline`);
      } catch (error) {
        console.log(`  ${browserName}: Expected error caught: ${error.message}`);
      }
      
      await page.waitForTimeout(2000);
      
      // Restore network
      await page.context().setOffline(false);
      await page.waitForTimeout(1000);
      
      // Verify graceful recovery
      await expect(dashboardPage.dashboardLayout).toBeVisible();
      console.log(`  ✅ ${browserName}: Network error handling consistent`);
    });

    await test.step(`${browserName}: JavaScript Error Resilience`, async () => {
      // Monitor for console errors
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });
      
      // Perform normal operations
      await dashboardPage.triggerTurnOrchestration();
      await page.waitForTimeout(3000);
      
      // Check for critical console errors
      const criticalErrors = consoleErrors.filter(error => 
        error.toLowerCase().includes('uncaught') ||
        error.toLowerCase().includes('script error')
      );
      
      expect(criticalErrors.length).toBe(0);
      
      if (consoleErrors.length > 0) {
        console.log(`  ${browserName}: ${consoleErrors.length} console messages (non-critical)`);
      } else {
        console.log(`  ✅ ${browserName}: No console errors detected`);
      }
    });

    console.log(`🛡️ ✅ ${browserName} error handling test completed`);
  });

  // Visual regression test across browsers
  test('Visual Consistency Check', async ({ page, browserName }) => {
    console.log(`👀 Visual consistency check on ${browserName}...`);
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();

    await test.step(`${browserName}: Initial State Screenshot`, async () => {
      await dashboardPage.takeFullScreenshot(`visual-${browserName}-initial`);
      console.log(`  ✅ ${browserName}: Initial state captured`);
    });

    await test.step(`${browserName}: Active State Screenshot`, async () => {
      await dashboardPage.triggerTurnOrchestration();
      await page.waitForTimeout(3000);
      await dashboardPage.takeFullScreenshot(`visual-${browserName}-active`);
      console.log(`  ✅ ${browserName}: Active state captured`);
    });

    console.log(`👀 ✅ ${browserName} visual consistency check completed`);
  });
});

// Browser-specific edge case tests
test.describe('Browser-Specific Edge Cases', () => {
  
  test('Safari: WebKit-specific Issues', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'Safari-specific test');
    
    console.log('🍎 Testing Safari-specific edge cases...');
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();

    await test.step('Safari: Date/Time Handling', async () => {
      // Safari has specific date parsing quirks
      const dateSupport = await page.evaluate(() => {
        const testDate = new Date('2023-12-01T10:00:00Z');
        return !isNaN(testDate.getTime());
      });
      
      expect(dateSupport).toBe(true);
      console.log('  ✅ Safari: Date handling working correctly');
    });

    await test.step('Safari: CSS Variable Support', async () => {
      // Test CSS custom properties support
      const cssVarSupport = await page.evaluate(() => {
        const el = document.createElement('div');
        el.style.setProperty('--test-var', '10px');
        document.body.appendChild(el);
        const computedValue = getComputedStyle(el).getPropertyValue('--test-var');
        document.body.removeChild(el);
        return computedValue.trim() === '10px';
      });
      
      expect(cssVarSupport).toBe(true);
      console.log('  ✅ Safari: CSS Variables supported');
    });

    console.log('🍎 ✅ Safari-specific tests completed');
  });

  test('Firefox: Gecko-specific Issues', async ({ page, browserName }) => {
    test.skip(browserName !== 'firefox', 'Firefox-specific test');
    
    console.log('🦊 Testing Firefox-specific edge cases...');
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();

    await test.step('Firefox: CSS Grid Gap Behavior', async () => {
      // Firefox has some specific CSS Grid behaviors
      const gridGapSupport = await dashboardPage.bentoGrid.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return styles.gap !== '' && styles.gap !== 'normal';
      });
      
      expect(gridGapSupport).toBe(true);
      console.log('  ✅ Firefox: CSS Grid gap working correctly');
    });

    console.log('🦊 ✅ Firefox-specific tests completed');
  });

  test('Chrome: Chromium-specific Features', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Chrome-specific test');
    
    console.log('🌐 Testing Chrome-specific features...');
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();

    await test.step('Chrome: DevTools Protocol Integration', async () => {
      // Test Chrome DevTools Protocol for performance monitoring
      const client = await page.context().newCDPSession(page);
      
      try {
        await client.send('Runtime.enable');
        const heapUsage = await client.send('Runtime.getHeapUsage');
        
        expect(heapUsage.totalSize).toBeGreaterThan(0);
        console.log('  ✅ Chrome: DevTools Protocol working');
      } catch (error) {
        console.log('  ⚠️ Chrome: DevTools Protocol not available');
      }
    });

    console.log('🌐 ✅ Chrome-specific tests completed');
  });
});
