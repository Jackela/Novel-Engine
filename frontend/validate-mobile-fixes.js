import { chromium } from 'playwright';

async function validateMobileFixes() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 375, height: 667 }, // iPhone SE dimensions
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
  });

  const page = await context.newPage();

  try {
    console.log('🔍 Navigating to dashboard...');
    await page.goto('http://localhost:3004');
    
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="world-state-map"]', { timeout: 30000 });
    console.log('✅ Dashboard loaded successfully');

    // Wait for components to be fully rendered
    await page.waitForTimeout(3000);

    console.log('📱 Capturing mobile validation screenshots...');

    // Capture Real-time Activity component
    const activityComponent = await page.locator('[data-testid="real-time-activity"]');
    await activityComponent.screenshot({ 
      path: 'visual-diagnosis-screenshots/real-time-activity-mobile-FIXED-375x667.png' 
    });
    console.log('✅ Real-time Activity mobile screenshot captured');

    // Capture Performance Metrics component  
    const performanceComponent = await page.locator('[data-testid="performance-metrics"]');
    await performanceComponent.screenshot({ 
      path: 'visual-diagnosis-screenshots/performance-metrics-mobile-FIXED-375x667.png' 
    });
    console.log('✅ Performance Metrics mobile screenshot captured');

    // Capture full mobile dashboard for comparison
    await page.screenshot({ 
      path: 'visual-diagnosis-screenshots/dashboard-mobile-FIXED-375x667.png',
      fullPage: true 
    });
    console.log('✅ Full mobile dashboard screenshot captured');

    console.log('\n🎯 Mobile Information Density Validation Complete!');
    console.log('📊 Screenshots saved to: visual-diagnosis-screenshots/');
    console.log('   - real-time-activity-mobile-FIXED-375x667.png');
    console.log('   - performance-metrics-mobile-FIXED-375x667.png');
    console.log('   - dashboard-mobile-FIXED-375x667.png');

  } catch (error) {
    console.error('❌ Validation failed:', error.message);
  } finally {
    await browser.close();
  }
}

validateMobileFixes().catch(console.error);