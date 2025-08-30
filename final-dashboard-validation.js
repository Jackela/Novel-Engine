/**
 * Final Dashboard Validation Script
 * ================================
 * 
 * Comprehensive QA validation of the Emergent Narrative Dashboard
 * Tests desktop and mobile viewports with visual evidence capture
 * 
 * QA Methodology: Risk-based testing with production readiness criteria
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Test Configuration
const TEST_CONFIG = {
  baseUrl: 'http://localhost:3000',
  apiUrl: 'http://localhost:5000',
  screenshotDir: './final-validation-screenshots',
  timeout: 30000,
  
  // Viewport configurations matching UI specification
  viewports: {
    desktop: { width: 1440, height: 900 },    // Desktop spec: ≥1440px
    tablet: { width: 1024, height: 768 },     // Tablet spec: 768px-1439px  
    mobile: { width: 375, height: 667 }       // Mobile spec: ≤767px
  },
  
  // Production readiness criteria
  qualityGates: {
    maxLoadTime: 5000,        // 5s maximum load time
    minAccessibilityScore: 90, // 90% accessibility compliance
    requiredComponents: 9,     // All 9 dashboard components
    mobileButtonSize: 44       // WCAG minimum touch target
  }
};

// Global test results
const testResults = {
  timestamp: new Date().toISOString(),
  viewports: {},
  apiHealth: null,
  overallStatus: 'PENDING',
  criticalIssues: [],
  productionReady: false
};

/**
 * Initialize test environment and create screenshot directory
 */
async function initializeTest() {
  console.log('🔧 Initializing Final Dashboard Validation...');
  
  // Create screenshot directory
  if (!fs.existsSync(TEST_CONFIG.screenshotDir)) {
    fs.mkdirSync(TEST_CONFIG.screenshotDir, { recursive: true });
  }
  
  // Test API connectivity
  try {
    const response = await fetch(`${TEST_CONFIG.apiUrl}/health`);
    const health = await response.json();
    testResults.apiHealth = {
      status: health.status,
      accessible: true,
      responseTime: Date.now()
    };
    console.log('✅ Backend API health check passed');
  } catch (error) {
    testResults.apiHealth = {
      status: 'unhealthy',
      accessible: false,
      error: error.message
    };
    console.log('❌ Backend API health check failed:', error.message);
  }
}

/**
 * Test dashboard components and functionality for a specific viewport
 */
async function testViewport(browser, viewportName, viewportConfig) {
  console.log(`\n📱 Testing ${viewportName} viewport (${viewportConfig.width}x${viewportConfig.height})`);
  
  const context = await browser.newContext({
    viewport: viewportConfig,
    deviceScaleFactor: 1,
    hasTouch: viewportName === 'mobile'
  });
  
  const page = await context.newPage();
  const viewportResults = {
    name: viewportName,
    config: viewportConfig,
    loadTime: null,
    components: {},
    quickActions: {},
    screenshots: [],
    errors: [],
    passed: false
  };
  
  try {
    // Measure load time
    const startTime = Date.now();
    await page.goto(TEST_CONFIG.baseUrl, { 
      waitUntil: 'networkidle',
      timeout: TEST_CONFIG.timeout 
    });
    viewportResults.loadTime = Date.now() - startTime;
    
    console.log(`⏱️  Load time: ${viewportResults.loadTime}ms`);
    
    // Take full page screenshot
    const screenshotPath = path.join(TEST_CONFIG.screenshotDir, `${viewportName}-full-dashboard.png`);
    await page.screenshot({ 
      path: screenshotPath, 
      fullPage: true,
      timeout: 10000
    });
    viewportResults.screenshots.push(screenshotPath);
    console.log(`📸 Full dashboard screenshot: ${screenshotPath}`);
    
    // Test component visibility and functionality
    await testDashboardComponents(page, viewportResults);
    
    // Critical test: QuickActions component (mobile focus)
    await testQuickActionsComponent(page, viewportResults, viewportName);
    
    // Performance validation
    await validatePerformance(page, viewportResults);
    
    // Accessibility validation  
    await validateAccessibility(page, viewportResults);
    
    viewportResults.passed = viewportResults.errors.length === 0;
    console.log(`${viewportResults.passed ? '✅' : '❌'} ${viewportName} viewport validation ${viewportResults.passed ? 'PASSED' : 'FAILED'}`);
    
  } catch (error) {
    viewportResults.errors.push({
      type: 'critical',
      message: `Viewport test failed: ${error.message}`,
      timestamp: new Date().toISOString()
    });
    console.log(`❌ Critical error in ${viewportName} viewport:`, error.message);
  } finally {
    await context.close();
  }
  
  return viewportResults;
}

/**
 * Test all dashboard components are present and visible
 */
async function testDashboardComponents(page, viewportResults) {
  console.log('🔍 Testing dashboard components...');
  
  // Expected dashboard components based on UI specification
  const expectedComponents = [
    { name: 'World State Map', selector: '[data-testid*="world"], [data-testid*="map"]', required: true },
    { name: 'Real-time Activity', selector: '[data-testid*="activity"], [data-testid*="feed"]', required: true },
    { name: 'Performance Metrics', selector: '[data-testid*="metrics"], [data-testid*="performance"]', required: true },
    { name: 'Turn Pipeline', selector: '[data-testid*="pipeline"], [data-testid*="turn"]', required: true },
    { name: 'Quick Actions', selector: '[data-testid="quick-actions"]', required: true },
    { name: 'Character Networks', selector: '[data-testid*="character"], [data-testid*="network"]', required: true },
    { name: 'Event Cascade', selector: '[data-testid*="cascade"], [data-testid*="event"]', required: true },
    { name: 'Narrative Timeline', selector: '[data-testid*="timeline"], [data-testid*="narrative"]', required: true },
    { name: 'Analytics Dashboard', selector: '[data-testid*="analytics"], [data-testid*="dashboard"]', required: false }
  ];
  
  let visibleComponents = 0;
  
  for (const component of expectedComponents) {
    try {
      const element = await page.$(component.selector);
      const isVisible = element ? await element.isVisible() : false;
      
      viewportResults.components[component.name] = {
        selector: component.selector,
        present: !!element,
        visible: isVisible,
        required: component.required
      };
      
      if (isVisible) {
        visibleComponents++;
        console.log(`  ✅ ${component.name}: Present and visible`);
      } else if (component.required) {
        viewportResults.errors.push({
          type: 'component_missing',
          message: `Required component missing: ${component.name}`,
          selector: component.selector
        });
        console.log(`  ❌ ${component.name}: Missing or not visible`);
      } else {
        console.log(`  ⚠️  ${component.name}: Optional component not visible`);
      }
      
    } catch (error) {
      viewportResults.errors.push({
        type: 'component_error',
        message: `Error testing ${component.name}: ${error.message}`,
        selector: component.selector
      });
    }
  }
  
  console.log(`📊 Components visible: ${visibleComponents}/${expectedComponents.length}`);
}

/**
 * Critical test: QuickActions component functionality (especially mobile)
 */
async function testQuickActionsComponent(page, viewportResults, viewportName) {
  console.log('🎯 Testing QuickActions component (Critical Test)...');
  
  try {
    const quickActionsSelector = '[data-testid="quick-actions"]';
    const quickActions = await page.$(quickActionsSelector);
    
    if (!quickActions) {
      viewportResults.errors.push({
        type: 'critical',
        message: 'QuickActions component not found - this was the main fix target!'
      });
      return;
    }
    
    // Get component dimensions and visibility
    const boundingBox = await quickActions.boundingBox();
    const isVisible = await quickActions.isVisible();
    
    viewportResults.quickActions = {
      present: true,
      visible: isVisible,
      dimensions: boundingBox,
      buttons: []
    };
    
    console.log(`  📐 QuickActions dimensions: ${boundingBox?.width}x${boundingBox?.height}`);
    
    // Test action buttons (critical for mobile UX)
    const actionButtons = await page.$$(`${quickActionsSelector} button`);
    console.log(`  🔘 Found ${actionButtons.length} action buttons`);
    
    for (let i = 0; i < actionButtons.length; i++) {
      const button = actionButtons[i];
      const buttonBox = await button.boundingBox();
      const isButtonVisible = await button.isVisible();
      const isEnabled = await button.isEnabled();
      
      viewportResults.quickActions.buttons.push({
        index: i,
        visible: isButtonVisible,
        enabled: isEnabled,
        dimensions: buttonBox,
        touchFriendly: viewportName === 'mobile' ? 
          (buttonBox?.width >= TEST_CONFIG.qualityGates.mobileButtonSize && 
           buttonBox?.height >= TEST_CONFIG.qualityGates.mobileButtonSize) : true
      });
      
      if (viewportName === 'mobile' && buttonBox) {
        const isTouchFriendly = buttonBox.width >= 44 && buttonBox.height >= 44;
        console.log(`    Button ${i + 1}: ${buttonBox.width}x${buttonBox.height} - ${isTouchFriendly ? 'Touch-friendly ✅' : 'Too small for touch ❌'}`);
        
        if (!isTouchFriendly) {
          viewportResults.errors.push({
            type: 'accessibility',
            message: `QuickActions button ${i + 1} too small for mobile (${buttonBox.width}x${buttonBox.height}, minimum 44x44)`
          });
        }
      }
    }
    
    // Test primary action button specifically
    const runTurnButton = await page.$('[data-testid="run-turn-button"]');
    if (runTurnButton) {
      const isVisible = await runTurnButton.isVisible();
      const isEnabled = await runTurnButton.isEnabled();
      console.log(`  ▶️  Run Turn button: Visible=${isVisible}, Enabled=${isEnabled}`);
      
      viewportResults.quickActions.primaryAction = {
        present: true,
        visible: isVisible,
        enabled: isEnabled
      };
    } else {
      viewportResults.errors.push({
        type: 'functionality',
        message: 'Primary "Run Turn" button not found in QuickActions'
      });
    }
    
    // Take focused screenshot of QuickActions
    const componentScreenshot = path.join(TEST_CONFIG.screenshotDir, `${viewportName}-quick-actions-detail.png`);
    await quickActions.screenshot({ path: componentScreenshot });
    viewportResults.screenshots.push(componentScreenshot);
    console.log(`  📸 QuickActions detail screenshot: ${componentScreenshot}`);
    
  } catch (error) {
    viewportResults.errors.push({
      type: 'critical',
      message: `QuickActions test failed: ${error.message}`
    });
    console.log(`❌ QuickActions test error:`, error.message);
  }
}

/**
 * Validate performance metrics
 */
async function validatePerformance(page, viewportResults) {
  console.log('⚡ Validating performance...');
  
  try {
    // Check load time against quality gates
    if (viewportResults.loadTime > TEST_CONFIG.qualityGates.maxLoadTime) {
      viewportResults.errors.push({
        type: 'performance',
        message: `Load time ${viewportResults.loadTime}ms exceeds maximum ${TEST_CONFIG.qualityGates.maxLoadTime}ms`
      });
    }
    
    // Check for console errors that might indicate performance issues
    const logs = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        logs.push(msg.text());
      }
    });
    
    // Wait a moment to capture any async errors
    await page.waitForTimeout(2000);
    
    if (logs.length > 0) {
      viewportResults.errors.push({
        type: 'performance',
        message: `Console errors detected: ${logs.join(', ')}`
      });
    }
    
    console.log(`  ⏱️  Load time: ${viewportResults.loadTime}ms (${viewportResults.loadTime <= TEST_CONFIG.qualityGates.maxLoadTime ? 'PASS' : 'FAIL'})`);
    
  } catch (error) {
    console.log(`⚠️  Performance validation error:`, error.message);
  }
}

/**
 * Basic accessibility validation
 */
async function validateAccessibility(page, viewportResults) {
  console.log('♿ Validating accessibility...');
  
  try {
    // Check for basic accessibility attributes
    const accessibilityChecks = [
      { name: 'Focus indicators', selector: ':focus-visible', required: false },
      { name: 'Alt text for images', selector: 'img:not([alt])', shouldBeEmpty: true },
      { name: 'ARIA labels', selector: '[aria-label], [aria-labelledby]', required: false },
      { name: 'Headings structure', selector: 'h1, h2, h3, h4, h5, h6', required: true }
    ];
    
    for (const check of accessibilityChecks) {
      const elements = await page.$$(check.selector);
      
      if (check.shouldBeEmpty && elements.length > 0) {
        viewportResults.errors.push({
          type: 'accessibility',
          message: `${check.name}: Found ${elements.length} elements missing accessibility attributes`
        });
      } else if (check.required && elements.length === 0) {
        viewportResults.errors.push({
          type: 'accessibility', 
          message: `${check.name}: No elements found (may indicate accessibility issue)`
        });
      }
    }
    
    console.log(`  ♿ Basic accessibility checks completed`);
    
  } catch (error) {
    console.log(`⚠️  Accessibility validation error:`, error.message);
  }
}

/**
 * Generate comprehensive test report
 */
function generateReport() {
  console.log('\n📋 Generating Final Validation Report...');
  
  // Determine overall status
  const allViewportsPassed = Object.values(testResults.viewports).every(v => v.passed);
  const hasApiHealth = testResults.apiHealth?.accessible;
  const noCriticalIssues = testResults.criticalIssues.length === 0;
  
  testResults.productionReady = allViewportsPassed && hasApiHealth && noCriticalIssues;
  testResults.overallStatus = testResults.productionReady ? 'PRODUCTION READY' : 'REQUIRES ATTENTION';
  
  // Count critical issues across all viewports
  for (const viewport of Object.values(testResults.viewports)) {
    const criticalErrors = viewport.errors.filter(e => e.type === 'critical' || e.type === 'component_missing');
    testResults.criticalIssues.push(...criticalErrors.map(e => ({
      viewport: viewport.name,
      ...e
    })));
  }
  
  const reportSummary = {
    timestamp: testResults.timestamp,
    overallStatus: testResults.overallStatus,
    productionReady: testResults.productionReady,
    viewportResults: Object.keys(testResults.viewports).map(name => ({
      viewport: name,
      passed: testResults.viewports[name].passed,
      loadTime: testResults.viewports[name].loadTime,
      componentCount: Object.keys(testResults.viewports[name].components).length,
      errorCount: testResults.viewports[name].errors.length,
      quickActionsWorking: testResults.viewports[name].quickActions?.present && 
                          testResults.viewports[name].quickActions?.visible
    })),
    apiHealth: testResults.apiHealth,
    criticalIssues: testResults.criticalIssues.length,
    screenshots: []
  };
  
  // Collect all screenshots
  for (const viewport of Object.values(testResults.viewports)) {
    reportSummary.screenshots.push(...viewport.screenshots.map(s => ({
      viewport: viewport.name,
      path: s,
      type: s.includes('quick-actions') ? 'component-detail' : 'full-dashboard'
    })));
  }
  
  // Save detailed results
  fs.writeFileSync(
    path.join(TEST_CONFIG.screenshotDir, 'validation-results.json'),
    JSON.stringify(testResults, null, 2)
  );
  
  console.log(`\n🎯 FINAL VALIDATION RESULT: ${testResults.overallStatus}`);
  console.log(`📊 Production Ready: ${testResults.productionReady ? '✅ YES' : '❌ NO'}`);
  console.log(`🔧 API Health: ${testResults.apiHealth?.accessible ? '✅ Healthy' : '❌ Unhealthy'}`);
  console.log(`📱 Viewports Tested: ${Object.keys(testResults.viewports).length}`);
  console.log(`⚠️  Critical Issues: ${testResults.criticalIssues.length}`);
  console.log(`📸 Screenshots Captured: ${reportSummary.screenshots.length}`);
  
  return reportSummary;
}

/**
 * Main test execution function
 */
async function runFinalValidation() {
  const startTime = Date.now();
  console.log('🚀 Starting Final Dashboard Validation\n');
  
  await initializeTest();
  
  const browser = await chromium.launch({ headless: true });
  
  try {
    // Test all viewports
    for (const [name, config] of Object.entries(TEST_CONFIG.viewports)) {
      testResults.viewports[name] = await testViewport(browser, name, config);
    }
    
  } catch (error) {
    console.error('❌ Test execution failed:', error);
    testResults.criticalIssues.push({
      type: 'execution_failure',
      message: error.message
    });
  } finally {
    await browser.close();
  }
  
  const report = generateReport();
  const totalTime = Date.now() - startTime;
  
  console.log(`\n⏱️  Total execution time: ${totalTime}ms`);
  console.log(`📁 Results saved to: ${TEST_CONFIG.screenshotDir}/`);
  
  return report;
}

// Execute validation if run directly
if (require.main === module) {
  runFinalValidation()
    .then(report => {
      process.exit(report.productionReady ? 0 : 1);
    })
    .catch(error => {
      console.error('❌ Validation failed:', error);
      process.exit(1);
    });
}

module.exports = { runFinalValidation, TEST_CONFIG };