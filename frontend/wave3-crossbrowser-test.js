/**
 * WAVE 3: CROSS-BROWSER TESTING
 * Validate UI consistency and functionality across Chrome, Firefox, and Safari
 */

import { chromium, firefox, webkit } from 'playwright';
import fs from 'fs';

async function executeCrossBrowserTest() {
  console.log('🌐 WAVE 3: CROSS-BROWSER TESTING - Validating UI consistency across browsers...');
  
  const results = {
    timestamp: new Date().toISOString(),
    testType: 'cross_browser_validation',
    browsers: {
      chromium: { tested: false, results: null },
      firefox: { tested: false, results: null },
      webkit: { tested: false, results: null }
    },
    consistency: {
      score: 0,
      rating: 'unknown',
      differences: []
    },
    overall: {
      compatible: false,
      rating: 'unknown'
    }
  };

  const startTime = Date.now();

  // Define test scenarios for each browser
  const testScenarios = [
    { name: 'page_load', description: 'Page loading and initial render' },
    { name: 'ui_elements', description: 'UI element visibility and styling' },
    { name: 'interactions', description: 'Button clicks and user interactions' },
    { name: 'responsive', description: 'Responsive design behavior' }
  ];

  console.log('🧪 Testing scenarios:', testScenarios.map(s => s.name).join(', '));

  async function testBrowser(browserType, browserName) {
    console.log(`\n🔍 Testing ${browserName.toUpperCase()}...`);
    
    const browserResults = {
      name: browserName,
      scenarios: {},
      performance: {},
      compatibility: 'unknown',
      screenshots: []
    };

    let browser, page;
    
    try {
      // Launch browser
      browser = await browserType.launch({ headless: false });
      const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
      });
      page = await context.newPage();

      // Monitor console errors
      const errors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // Scenario 1: Page Load Test
      console.log(`  📏 ${browserName}: Page load test...`);
      const loadStart = Date.now();
      
      try {
        await page.goto('http://localhost:3002/dashboard', { 
          waitUntil: 'networkidle',
          timeout: 30000
        });
        
        const loadTime = Date.now() - loadStart;
        
        browserResults.scenarios.page_load = {
          success: true,
          loadTime,
          rating: loadTime <= 3000 ? 'excellent' : loadTime <= 5000 ? 'good' : 'poor'
        };
        
        console.log(`    ✅ Load time: ${loadTime}ms`);
        
      } catch (loadError) {
        browserResults.scenarios.page_load = {
          success: false,
          error: loadError.message
        };
        console.log(`    ❌ Load failed: ${loadError.message}`);
      }

      // Take initial screenshot
      const initialScreenshot = `wave3-${browserName}-initial-${Date.now()}.png`;
      await page.screenshot({ path: initialScreenshot, fullPage: true });
      browserResults.screenshots.push(initialScreenshot);
      console.log(`    📸 Screenshot: ${initialScreenshot}`);

      // Scenario 2: UI Elements Test
      console.log(`  🎨 ${browserName}: UI elements test...`);
      
      try {
        const uiAnalysis = await page.evaluate(() => {
          // Check for key UI elements
          const tiles = document.querySelectorAll('.MuiPaper-root, [class*="tile"]');
          const buttons = document.querySelectorAll('button:not([disabled])');
          const chips = document.querySelectorAll('.MuiChip-root');
          
          // Check styling consistency
          const backgroundColor = getComputedStyle(document.body).backgroundColor;
          const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--color-primary') || 'not-set';
          
          return {
            tilesCount: tiles.length,
            buttonsCount: buttons.length,
            chipsCount: chips.length,
            backgroundColor,
            primaryColor,
            title: document.title,
            professionalTheme: backgroundColor.includes('10, 10, 11') || backgroundColor === 'rgb(10, 10, 11)'
          };
        });

        browserResults.scenarios.ui_elements = {
          success: true,
          ...uiAnalysis,
          rating: uiAnalysis.tilesCount >= 8 && uiAnalysis.buttonsCount >= 8 ? 'excellent' : 'good'
        };
        
        console.log(`    ✅ Tiles: ${uiAnalysis.tilesCount}, Buttons: ${uiAnalysis.buttonsCount}, Theme: ${uiAnalysis.professionalTheme ? 'Professional' : 'Standard'}`);
        
      } catch (uiError) {
        browserResults.scenarios.ui_elements = {
          success: false,
          error: uiError.message
        };
        console.log(`    ❌ UI analysis failed: ${uiError.message}`);
      }

      // Scenario 3: Interactions Test
      console.log(`  ⚡ ${browserName}: Interactions test...`);
      
      try {
        const buttons = await page.$$('button:not([disabled])');
        const interactionResults = [];
        const testCount = Math.min(buttons.length, 5);
        
        for (let i = 0; i < testCount; i++) {
          const interactionStart = Date.now();
          
          try {
            await buttons[i].click();
            await page.waitForTimeout(200);
            
            const responseTime = Date.now() - interactionStart;
            interactionResults.push({
              buttonIndex: i,
              responseTime,
              success: true
            });
            
          } catch (clickError) {
            interactionResults.push({
              buttonIndex: i,
              success: false,
              error: clickError.message
            });
          }
        }
        
        const avgResponseTime = interactionResults.filter(r => r.success)
          .reduce((sum, r) => sum + r.responseTime, 0) / interactionResults.filter(r => r.success).length;
        
        browserResults.scenarios.interactions = {
          success: true,
          interactionResults,
          averageResponseTime: avgResponseTime || 0,
          rating: avgResponseTime <= 300 ? 'excellent' : avgResponseTime <= 500 ? 'good' : 'acceptable'
        };
        
        console.log(`    ✅ Average response: ${Math.round(avgResponseTime)}ms`);
        
      } catch (interactionError) {
        browserResults.scenarios.interactions = {
          success: false,
          error: interactionError.message
        };
        console.log(`    ❌ Interactions failed: ${interactionError.message}`);
      }

      // Scenario 4: Responsive Test
      console.log(`  📱 ${browserName}: Responsive test...`);
      
      try {
        // Test mobile viewport
        await page.setViewportSize({ width: 390, height: 844 });
        await page.waitForTimeout(1000);
        
        const mobileScreenshot = `wave3-${browserName}-mobile-${Date.now()}.png`;
        await page.screenshot({ path: mobileScreenshot, fullPage: true });
        browserResults.screenshots.push(mobileScreenshot);
        
        const mobileAnalysis = await page.evaluate(() => {
          const tiles = document.querySelectorAll('.MuiPaper-root, [class*="tile"]');
          const buttons = document.querySelectorAll('button');
          
          // Check if elements are still visible and properly sized
          let visibleTiles = 0;
          tiles.forEach(tile => {
            const rect = tile.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) visibleTiles++;
          });
          
          return {
            visibleTiles,
            totalButtons: buttons.length,
            viewportWidth: window.innerWidth,
            responsive: visibleTiles > 0
          };
        });
        
        // Reset to desktop viewport
        await page.setViewportSize({ width: 1920, height: 1080 });
        
        browserResults.scenarios.responsive = {
          success: true,
          mobileAnalysis,
          rating: mobileAnalysis.responsive ? 'excellent' : 'poor'
        };
        
        console.log(`    ✅ Mobile responsive: ${mobileAnalysis.responsive ? 'Yes' : 'No'}`);
        console.log(`    📸 Mobile screenshot: ${mobileScreenshot}`);
        
      } catch (responsiveError) {
        browserResults.scenarios.responsive = {
          success: false,
          error: responsiveError.message
        };
        console.log(`    ❌ Responsive test failed: ${responsiveError.message}`);
      }

      // Calculate browser compatibility score
      const successfulScenarios = Object.values(browserResults.scenarios).filter(s => s.success).length;
      const totalScenarios = testScenarios.length;
      const compatibilityScore = (successfulScenarios / totalScenarios) * 100;
      
      browserResults.compatibility = compatibilityScore >= 90 ? 'excellent' : 
        compatibilityScore >= 75 ? 'good' : 
        compatibilityScore >= 50 ? 'acceptable' : 'poor';
      browserResults.compatibilityScore = Math.round(compatibilityScore);
      browserResults.consoleErrors = errors.length;

      console.log(`  📊 ${browserName} Compatibility: ${browserResults.compatibility.toUpperCase()} (${compatibilityScore.toFixed(1)}%)`);
      console.log(`  ⚠️  Console Errors: ${errors.length}`);

      await browser.close();
      return browserResults;
      
    } catch (error) {
      console.error(`❌ Critical error testing ${browserName}:`, error);
      
      if (browser) {
        try {
          await browser.close();
        } catch (closeError) {
          console.error(`Error closing ${browserName}:`, closeError);
        }
      }
      
      return {
        name: browserName,
        compatibility: 'failed',
        error: error.message,
        screenshots: []
      };
    }
  }

  try {
    // Test all browsers
    console.log('🔄 Starting cross-browser validation...');
    
    // Test Chromium
    results.browsers.chromium.results = await testBrowser(chromium, 'chromium');
    results.browsers.chromium.tested = true;
    
    // Test Firefox
    results.browsers.firefox.results = await testBrowser(firefox, 'firefox');
    results.browsers.firefox.tested = true;
    
    // Test WebKit (Safari)
    try {
      results.browsers.webkit.results = await testBrowser(webkit, 'webkit');
      results.browsers.webkit.tested = true;
    } catch (webkitError) {
      console.log('⚠️ WebKit/Safari testing not available on this system');
      results.browsers.webkit = {
        tested: false,
        error: 'WebKit not available on Windows',
        note: 'Safari testing requires macOS'
      };
    }

    // Analyze cross-browser consistency
    console.log('\n🔍 Analyzing cross-browser consistency...');
    
    const testedBrowsers = Object.entries(results.browsers)
      .filter(([_, browser]) => browser.tested && browser.results)
      .map(([name, browser]) => ({ name, ...browser.results }));
    
    if (testedBrowsers.length >= 2) {
      // Compare UI elements across browsers
      const uiComparison = testedBrowsers.map(browser => browser.scenarios.ui_elements);
      const tilesConsistent = new Set(uiComparison.filter(ui => ui.success).map(ui => ui.tilesCount)).size <= 1;
      const buttonsConsistent = new Set(uiComparison.filter(ui => ui.success).map(ui => ui.buttonsCount)).size <= 1;
      const themeConsistent = uiComparison.filter(ui => ui.success).every(ui => ui.professionalTheme);
      
      results.consistency.differences = [];
      if (!tilesConsistent) results.consistency.differences.push('Inconsistent tile counts across browsers');
      if (!buttonsConsistent) results.consistency.differences.push('Inconsistent button counts across browsers');
      if (!themeConsistent) results.consistency.differences.push('Theme not consistently applied across browsers');
      
      // Calculate overall consistency score
      const totalChecks = 3; // tiles, buttons, theme
      const passedChecks = [tilesConsistent, buttonsConsistent, themeConsistent].filter(Boolean).length;
      results.consistency.score = Math.round((passedChecks / totalChecks) * 100);
      results.consistency.rating = results.consistency.score >= 90 ? 'excellent' :
        results.consistency.score >= 75 ? 'good' : 
        results.consistency.score >= 50 ? 'acceptable' : 'poor';
    }

    // Overall compatibility assessment
    const compatibleBrowsers = testedBrowsers.filter(b => 
      b.compatibility === 'excellent' || b.compatibility === 'good'
    ).length;
    
    results.overall.compatible = compatibleBrowsers >= Math.max(1, testedBrowsers.length * 0.75);
    results.overall.rating = results.overall.compatible ? 'compatible' : 'issues_detected';

    // Final results summary
    console.log('\n🎯 WAVE 3 CROSS-BROWSER TESTING RESULTS:');
    
    testedBrowsers.forEach(browser => {
      console.log(`📊 ${browser.name.toUpperCase()}: ${browser.compatibility.toUpperCase()} (${browser.compatibilityScore}%)`);
    });
    
    if (results.browsers.webkit.error) {
      console.log(`📊 WEBKIT: NOT TESTED (${results.browsers.webkit.error})`);
    }
    
    console.log(`🔄 Consistency Score: ${results.consistency.score}% - ${results.consistency.rating.toUpperCase()}`);
    console.log(`🌐 Overall Compatibility: ${results.overall.rating.toUpperCase()}`);
    
    if (results.consistency.differences.length > 0) {
      console.log('⚠️ Differences detected:');
      results.consistency.differences.forEach(diff => console.log(`   - ${diff}`));
    }

    // Save detailed results
    const resultsFile = `wave3-crossbrowser-results-${Date.now()}.json`;
    fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
    console.log(`💾 Results saved: ${resultsFile}`);

    return results;
    
  } catch (error) {
    console.error('❌ Critical error in cross-browser testing:', error);
    results.criticalError = error.message;
    results.overall.rating = 'failed';
    return results;
  }
}

// Execute the test
executeCrossBrowserTest().then(results => {
  console.log(`\n🏁 Wave 3 Cross-Browser Test Complete! Rating: ${results.overall.rating}`);
  process.exit(results.overall.rating === 'failed' ? 1 : 0);
}).catch(console.error);