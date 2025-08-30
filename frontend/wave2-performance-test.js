/**
 * WAVE 2: PERFORMANCE VALIDATION
 * Benchmark response times, memory usage, and validate against performance thresholds
 */

import { chromium } from 'playwright';
import fs from 'fs';

async function executePerformanceTest() {
  console.log('⚡ WAVE 2: PERFORMANCE VALIDATION - Benchmarking system performance...');
  
  const results = {
    timestamp: new Date().toISOString(),
    testType: 'performance_validation',
    pageLoad: {
      times: [],
      average: 0,
      rating: 'unknown'
    },
    interactions: {
      responses: [],
      average: 0,
      rating: 'unknown'
    },
    memory: {
      samples: [],
      peak: 0,
      average: 0,
      efficiency: 'unknown'
    },
    rendering: {
      metrics: {},
      rating: 'unknown'
    },
    overall: {
      score: 0,
      rating: 'unknown'
    }
  };

  let browser, page;
  const startTime = Date.now();
  
  try {
    console.log('🚀 Launching browser for performance testing...');
    browser = await chromium.launch({ 
      headless: false,
      args: ['--enable-precise-memory-info', '--no-sandbox']
    });
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    page = await context.newPage();

    // Performance Test 1: Page Load Benchmarking
    console.log('📏 Testing page load performance (5 iterations)...');
    
    for (let i = 0; i < 5; i++) {
      const loadStart = Date.now();
      
      await page.goto('http://localhost:3002/dashboard', { 
        waitUntil: 'networkidle',
        timeout: 30000
      });
      
      const loadTime = Date.now() - loadStart;
      results.pageLoad.times.push(loadTime);
      
      console.log(`  Load ${i + 1}: ${loadTime}ms`);
      
      // Wait between loads
      if (i < 4) await page.waitForTimeout(1000);
    }

    // Calculate page load metrics
    results.pageLoad.average = results.pageLoad.times.reduce((sum, t) => sum + t, 0) / results.pageLoad.times.length;
    results.pageLoad.rating = results.pageLoad.average <= 2000 ? 'excellent' : 
      results.pageLoad.average <= 3000 ? 'good' : 
      results.pageLoad.average <= 5000 ? 'acceptable' : 'poor';

    console.log(`📊 Average Load Time: ${Math.round(results.pageLoad.average)}ms - ${results.pageLoad.rating.toUpperCase()}`);

    // Performance Test 2: Rendering Metrics
    console.log('🎨 Analyzing rendering performance...');
    
    const renderingMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      const paintEntries = performance.getEntriesByType('paint');
      
      return {
        domContentLoaded: navigation ? navigation.domContentLoadedEventEnd - navigation.navigationStart : 0,
        loadComplete: navigation ? navigation.loadEventEnd - navigation.navigationStart : 0,
        firstPaint: paintEntries.find(p => p.name === 'first-paint')?.startTime || 0,
        firstContentfulPaint: paintEntries.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
        domElements: document.querySelectorAll('*').length,
        interactiveElements: document.querySelectorAll('button, input, select, textarea, [role="button"]').length
      };
    });

    results.rendering.metrics = renderingMetrics;
    results.rendering.rating = renderingMetrics.firstContentfulPaint <= 1500 ? 'excellent' :
      renderingMetrics.firstContentfulPaint <= 2500 ? 'good' : 
      renderingMetrics.firstContentfulPaint <= 4000 ? 'acceptable' : 'poor';

    console.log(`  DOM Content Loaded: ${Math.round(renderingMetrics.domContentLoaded)}ms`);
    console.log(`  First Contentful Paint: ${Math.round(renderingMetrics.firstContentfulPaint)}ms`);
    console.log(`  DOM Elements: ${renderingMetrics.domElements}`);
    console.log(`  Interactive Elements: ${renderingMetrics.interactiveElements}`);

    // Performance Test 3: Interaction Response Times
    console.log('🔄 Testing interaction response times...');
    
    const buttons = await page.$$('button:not([disabled])');
    const testInteractions = Math.min(buttons.length, 10);
    
    for (let i = 0; i < testInteractions; i++) {
      try {
        const interactionStart = Date.now();
        
        await buttons[i].click();
        await page.waitForTimeout(100); // Allow UI to respond
        
        const responseTime = Date.now() - interactionStart;
        const buttonText = await buttons[i].textContent() || `Button ${i + 1}`;
        
        results.interactions.responses.push({
          element: buttonText.trim(),
          responseTime,
          acceptable: responseTime <= 300
        });
        
        console.log(`  ${buttonText.trim()}: ${responseTime}ms`);
        
      } catch (error) {
        console.log(`  Button ${i + 1}: Error - ${error.message}`);
      }
    }

    // Calculate interaction metrics
    results.interactions.average = results.interactions.responses.length > 0 ?
      results.interactions.responses.reduce((sum, r) => sum + r.responseTime, 0) / results.interactions.responses.length : 0;
    results.interactions.rating = results.interactions.average <= 200 ? 'excellent' :
      results.interactions.average <= 300 ? 'good' :
      results.interactions.average <= 500 ? 'acceptable' : 'poor';

    console.log(`📊 Average Interaction Time: ${Math.round(results.interactions.average)}ms - ${results.interactions.rating.toUpperCase()}`);

    // Performance Test 4: Memory Usage Monitoring
    console.log('🧠 Monitoring memory usage patterns...');
    
    for (let sample = 0; sample < 15; sample++) {
      try {
        const memoryData = await page.evaluate(() => {
          if (performance.memory) {
            return {
              usedJSHeapSize: performance.memory.usedJSHeapSize,
              totalJSHeapSize: performance.memory.totalJSHeapSize,
              jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
            };
          }
          return null;
        });
        
        if (memoryData) {
          results.memory.samples.push({
            sample: sample + 1,
            timestamp: Date.now() - startTime,
            ...memoryData
          });
        }
        
        // Trigger some activity for memory testing
        if (sample % 3 === 0) {
          const randomButton = await page.$('button:not([disabled])');
          if (randomButton) {
            try {
              await randomButton.click();
              await page.waitForTimeout(100);
            } catch (e) {
              // Interaction failed, continue
            }
          }
        }
        
        await page.waitForTimeout(500);
        
      } catch (error) {
        console.log(`Memory sample ${sample + 1} failed: ${error.message}`);
      }
    }

    // Calculate memory metrics
    if (results.memory.samples.length > 0) {
      const memoryValues = results.memory.samples.map(s => s.usedJSHeapSize);
      results.memory.peak = Math.max(...memoryValues);
      results.memory.average = memoryValues.reduce((sum, m) => sum + m, 0) / memoryValues.length;
      
      const peakMB = results.memory.peak / (1024 * 1024);
      results.memory.efficiency = peakMB <= 50 ? 'excellent' :
        peakMB <= 100 ? 'good' :
        peakMB <= 200 ? 'acceptable' : 'concerning';
    }

    console.log(`📊 Peak Memory: ${Math.round(results.memory.peak / (1024 * 1024))}MB - ${results.memory.efficiency.toUpperCase()}`);
    console.log(`📊 Average Memory: ${Math.round(results.memory.average / (1024 * 1024))}MB`);

    // Overall Performance Score Calculation
    const pageLoadScore = results.pageLoad.rating === 'excellent' ? 100 : 
      results.pageLoad.rating === 'good' ? 80 :
      results.pageLoad.rating === 'acceptable' ? 60 : 40;
      
    const interactionScore = results.interactions.rating === 'excellent' ? 100 :
      results.interactions.rating === 'good' ? 80 :
      results.interactions.rating === 'acceptable' ? 60 : 40;
      
    const memoryScore = results.memory.efficiency === 'excellent' ? 100 :
      results.memory.efficiency === 'good' ? 80 :
      results.memory.efficiency === 'acceptable' ? 60 : 40;
      
    const renderingScore = results.rendering.rating === 'excellent' ? 100 :
      results.rendering.rating === 'good' ? 80 :
      results.rendering.rating === 'acceptable' ? 60 : 40;

    results.overall.score = Math.round((pageLoadScore + interactionScore + memoryScore + renderingScore) / 4);
    results.overall.rating = results.overall.score >= 90 ? 'excellent' :
      results.overall.score >= 75 ? 'good' :
      results.overall.score >= 60 ? 'acceptable' : 'poor';

    // Capture performance screenshot
    const perfScreenshot = `wave2-performance-${Date.now()}.png`;
    await page.screenshot({ path: perfScreenshot, fullPage: true });
    console.log(`📸 Performance screenshot: ${perfScreenshot}`);

    console.log('\n🎯 WAVE 2 PERFORMANCE VALIDATION RESULTS:');
    console.log(`📊 Overall Performance Score: ${results.overall.score}/100 - ${results.overall.rating.toUpperCase()}`);
    console.log(`🚀 Page Load: ${results.pageLoad.rating.toUpperCase()} (${Math.round(results.pageLoad.average)}ms)`);
    console.log(`⚡ Interactions: ${results.interactions.rating.toUpperCase()} (${Math.round(results.interactions.average)}ms)`);
    console.log(`🧠 Memory Usage: ${results.memory.efficiency.toUpperCase()} (${Math.round(results.memory.peak / (1024 * 1024))}MB peak)`);
    console.log(`🎨 Rendering: ${results.rendering.rating.toUpperCase()} (${Math.round(renderingMetrics.firstContentfulPaint)}ms FCP)`);

    // Save detailed results
    const resultsFile = `wave2-performance-results-${Date.now()}.json`;
    fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
    console.log(`💾 Results saved: ${resultsFile}`);

    await browser.close();
    return results;

  } catch (error) {
    console.error('❌ Critical error in performance test:', error);
    results.criticalError = error.message;
    results.overall.rating = 'failed';
    
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
executePerformanceTest().then(results => {
  console.log(`\n🏁 Wave 2 Performance Test Complete! Overall Rating: ${results.overall.rating}`);
  process.exit(results.overall.rating === 'failed' ? 1 : 0);
}).catch(console.error);