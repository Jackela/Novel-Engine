import { chromium } from 'playwright';

async function comprehensiveDashboardTest() {
  console.log('🎯 Running comprehensive dashboard UAT test...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--no-sandbox', '--disable-web-security']
  });
  
  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();
    
    console.log('🌐 Loading frontend at http://localhost:3000...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'domcontentloaded',
      timeout: 30000 
    });
    
    // Wait for React app to initialize
    console.log('⏳ Waiting for React app to initialize...');
    await page.waitForTimeout(5000);
    
    // Check if we're redirected to dashboard
    const currentUrl = page.url();
    console.log('🔗 Current URL:', currentUrl);
    
    // Look for Material-UI and React components
    console.log('🔍 Searching for React/Material-UI components...');
    
    // Wait for any Material-UI component to appear
    const materialUISelectors = [
      '.MuiContainer-root',
      '.MuiPaper-root', 
      '.MuiCard-root',
      '.MuiGrid-root',
      '.MuiBox-root',
      '.MuiTypography-root',
      '.MuiButton-root',
      '.MuiAppBar-root'
    ];
    
    let foundMaterialUI = false;
    for (const selector of materialUISelectors) {
      try {
        await page.waitForSelector(selector, { timeout: 2000 });
        console.log(`✅ Found Material-UI component: ${selector}`);
        foundMaterialUI = true;
        break;
      } catch (e) {
        // Continue to next selector
      }
    }
    
    if (!foundMaterialUI) {
      console.log('⚠️ No Material-UI components found yet, checking for dashboard-specific elements...');
    }
    
    // Look for dashboard-specific elements
    const dashboardSelectors = [
      '[data-testid="dashboard-layout"]',
      '[data-testid="world-state-map"]',
      '[data-testid="real-time-activity"]',
      '[data-testid="turn-pipeline-status"]',
      '[data-testid="quick-actions"]',
      '.dashboard',
      '.bento-grid'
    ];
    
    let foundDashboard = false;
    for (const selector of dashboardSelectors) {
      const element = await page.$(selector);
      if (element) {
        console.log(`✅ Found dashboard element: ${selector}`);
        foundDashboard = true;
      }
    }
    
    // Check for the run_turn button specifically
    console.log('🎮 Looking for run_turn orchestration button...');
    const playButtonSelectors = [
      '[data-testid="play-button"]',
      '[data-testid="run-turn-button"]',
      'button[aria-label*="play"]',
      'button[aria-label*="run"]',
      '.MuiIconButton-root:has(svg)',
      'button:has([data-testid="PlayArrowIcon"])'
    ];
    
    let foundPlayButton = false;
    for (const selector of playButtonSelectors) {
      const button = await page.$(selector);
      if (button) {
        console.log(`🎯 Found play/run button: ${selector}`);
        foundPlayButton = true;
        
        // Test if button is interactive
        const isEnabled = await button.isEnabled();
        const isVisible = await button.isVisible();
        console.log(`  - Enabled: ${isEnabled}, Visible: ${isVisible}`);
        break;
      }
    }
    
    // Get rendered content analysis
    console.log('\n📊 Content Analysis:');
    const bodyContent = await page.evaluate(() => {
      const root = document.getElementById('root');
      return {
        hasContent: root && root.innerHTML.trim().length > 100,
        childCount: root ? root.children.length : 0,
        innerHTML: root ? root.innerHTML.slice(0, 300) + '...' : 'No root element'
      };
    });
    
    console.log('  - Root has content:', bodyContent.hasContent);
    console.log('  - Root child count:', bodyContent.childCount);
    console.log('  - Root content preview:', bodyContent.innerHTML);
    
    // Take screenshot
    await page.screenshot({ 
      path: 'comprehensive-dashboard-test.png', 
      fullPage: true 
    });
    console.log('📸 Screenshot saved as comprehensive-dashboard-test.png');
    
    // Final assessment
    console.log('\n📋 UAT Assessment:');
    const dashboardAccessible = foundMaterialUI || foundDashboard || bodyContent.hasContent;
    console.log('✅ Dashboard Accessible:', dashboardAccessible);
    console.log('✅ Material-UI Components:', foundMaterialUI);
    console.log('✅ Dashboard Elements:', foundDashboard);
    console.log('✅ Run/Turn Button:', foundPlayButton);
    
    if (dashboardAccessible) {
      console.log('\n🎉 Frontend is ready for UAT execution!');
      return {
        success: true,
        dashboardAccessible: dashboardAccessible,
        componentsFound: foundMaterialUI,
        dashboardElementsFound: foundDashboard,
        runTurnButtonFound: foundPlayButton,
        url: currentUrl
      };
    } else {
      console.log('\n⚠️ Frontend not fully ready - React app may not be rendering');
      return {
        success: false,
        dashboardAccessible: false,
        componentsFound: foundMaterialUI,
        dashboardElementsFound: foundDashboard,
        runTurnButtonFound: foundPlayButton,
        url: currentUrl
      };
    }
    
  } catch (error) {
    console.log('❌ Test failed:', error.message);
    return { success: false, error: error.message };
  } finally {
    await browser.close();
  }
}

// Run the test
comprehensiveDashboardTest().then(result => {
  console.log('\n📈 Final Result:', result);
  if (result.success) {
    console.log('\n✅ Ready to proceed with Wave 3: Core UAT Execution');
  } else {
    console.log('\n❌ Frontend needs additional fixes before UAT');
  }
  process.exit(result.success ? 0 : 1);
}).catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});