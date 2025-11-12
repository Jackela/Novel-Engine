/**
 * WAVE 1: STRESS TEST
 * Intensive UI interaction testing for stability validation
 */

import { chromium } from 'playwright';
import fs from 'fs';

async function executeStressTest() {
  console.log('🔥 WAVE 1: STRESS TEST - Starting intensive UI interaction testing...');
  
  const results = {
    timestamp: new Date().toISOString(),
    testType: 'stress_test',
    interactions: 0,
    duration: 0,
    errors: [],
    memoryPeaks: [],
    responseTracking: [],
    stability: 'unknown'
  };

  let browser, page;
  const startTime = Date.now();
  
  try {
    console.log('🚀 Launching browser for stress test...');
    browser = await chromium.launch({ headless: false, slowMo: 50 });
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    page = await context.newPage();

    // Monitor errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        results.errors.push({
          type: 'console_error',
          message: msg.text(),
          timestamp: Date.now() - startTime
        });
      }
    });

    console.log('📍 Navigating to dashboard...');
    await page.goto('http://localhost:3002/dashboard', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Capture initial state
    const initialScreenshot = `wave1-stress-initial-${Date.now()}.png`;
    await page.screenshot({ path: initialScreenshot, fullPage: true });
    console.log(`📸 Initial screenshot: ${initialScreenshot}`);

    console.log('💥 Beginning intensive interaction stress test (30 seconds)...');
    
    const testDuration = 30000; // 30 seconds
    const endTime = Date.now() + testDuration;
    let interactionCount = 0;

    while (Date.now() < endTime && interactionCount < 200) {
      try {
        const interactionStart = Date.now();
        
        // Get all clickable elements
        const buttons = await page.$$('button:not([disabled])');
        const chips = await page.$$('.MuiChip-root');
        const tiles = await page.$$('.MuiPaper-root');
        
        const allElements = [...buttons, ...chips, ...tiles].filter(Boolean);
        
        if (allElements.length > 0) {
          // Random element interaction
          const randomIndex = Math.floor(Math.random() * allElements.length);
          const element = allElements[randomIndex];
          
          try {
            await element.click();
            interactionCount++;
            
            const responseTime = Date.now() - interactionStart;
            results.responseTracking.push({
              interaction: interactionCount,
              responseTime,
              timestamp: Date.now() - startTime
            });

            // Log progress every 25 interactions
            if (interactionCount % 25 === 0) {
              console.log(`⚡ ${interactionCount} interactions completed - Last response: ${responseTime}ms`);
            }

          } catch (clickError) {
            results.errors.push({
              type: 'click_error',
              message: clickError.message,
              interaction: interactionCount,
              timestamp: Date.now() - startTime
            });
          }
        }

        // Memory sampling every 10 interactions
        if (interactionCount % 10 === 0) {
          try {
            const memory = await page.evaluate(() => {
              if (performance.memory) {
                return performance.memory.usedJSHeapSize;
              }
              return null;
            });
            if (memory) {
              results.memoryPeaks.push({
                interaction: interactionCount,
                memoryUsage: memory,
                timestamp: Date.now() - startTime
              });
            }
          } catch (memError) {
            // Memory monitoring failed, continue
          }
        }

        // Brief pause to prevent browser lockup
        await page.waitForTimeout(50);
        
      } catch (error) {
        results.errors.push({
          type: 'interaction_loop_error',
          message: error.message,
          interaction: interactionCount,
          timestamp: Date.now() - startTime
        });
      }
    }

    // Final screenshot and metrics
    const finalScreenshot = `wave1-stress-final-${Date.now()}.png`;
    await page.screenshot({ path: finalScreenshot, fullPage: true });
    console.log(`📸 Final screenshot: ${finalScreenshot}`);

    // Calculate results
    results.interactions = interactionCount;
    results.duration = Date.now() - startTime;
    results.averageResponseTime = results.responseTracking.length > 0 ? 
      results.responseTracking.reduce((sum, r) => sum + r.responseTime, 0) / results.responseTracking.length : 0;
    results.maxMemoryUsage = results.memoryPeaks.length > 0 ? 
      Math.max(...results.memoryPeaks.map(m => m.memoryUsage)) : 0;
    results.stability = results.errors.length === 0 ? 'excellent' : 
      results.errors.length <= 3 ? 'good' : results.errors.length <= 10 ? 'acceptable' : 'concerning';

    console.log('\n🎯 WAVE 1 STRESS TEST RESULTS:');
    console.log(`✅ Total Interactions: ${results.interactions}`);
    console.log(`⏱️ Duration: ${Math.round(results.duration / 1000)} seconds`);
    console.log(`📊 Average Response: ${Math.round(results.averageResponseTime)}ms`);
    console.log(`🧠 Peak Memory: ${Math.round(results.maxMemoryUsage / 1024 / 1024)}MB`);
    console.log(`🛡️ Stability: ${results.stability.toUpperCase()}`);
    console.log(`⚠️ Errors: ${results.errors.length}`);

    // Save detailed results
    const resultsFile = `wave1-stress-results-${Date.now()}.json`;
    fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
    console.log(`💾 Results saved: ${resultsFile}`);

    await browser.close();
    return results;

  } catch (error) {
    console.error('❌ Critical error in stress test:', error);
    results.criticalError = error.message;
    results.stability = 'failed';
    
    if (browser) {
      try {
        await browser.close();
      } catch (closeError) {
        console.error('Error closing browser:', closeError);
      }
    }
    
    return results;
  }
}

// Execute the test
executeStressTest().then(results => {
  console.log(`\n🏁 Wave 1 Stress Test Complete! Stability: ${results.stability}`);
  process.exit(results.stability === 'failed' ? 1 : 0);
}).catch(console.error);