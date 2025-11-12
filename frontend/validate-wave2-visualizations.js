import { chromium } from 'playwright';

async function validateWave2Visualizations() {
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

    console.log('📊 Capturing Wave 2 visualization screenshots...');

    // Capture Event Cascade Flow component
    const eventFlowComponent = page.locator('text=Event Cascade Flow').locator('..').locator('..');
    await eventFlowComponent.screenshot({ 
      path: 'visual-diagnosis-screenshots/event-cascade-flow-mobile-ENHANCED-375x667.png' 
    });
    console.log('✅ Event Cascade Flow mobile screenshot captured');

    // Capture Narrative Timeline component  
    const timelineComponent = page.locator('text=Narrative Arc Timeline').locator('..').locator('..');
    await timelineComponent.screenshot({ 
      path: 'visual-diagnosis-screenshots/narrative-timeline-mobile-ENHANCED-375x667.png' 
    });
    console.log('✅ Narrative Timeline mobile screenshot captured');

    // Capture Character Networks component for comparison
    const characterNetworksComponent = page.locator('text=Character Networks').locator('..').locator('..');
    await characterNetworksComponent.screenshot({ 
      path: 'visual-diagnosis-screenshots/character-networks-mobile-CURRENT-375x667.png' 
    });
    console.log('✅ Character Networks mobile screenshot captured');

    // Capture full mobile dashboard for progress comparison
    await page.screenshot({ 
      path: 'visual-diagnosis-screenshots/dashboard-mobile-WAVE2-375x667.png',
      fullPage: true 
    });
    console.log('✅ Full mobile dashboard Wave 2 screenshot captured');

    console.log('\n🎯 Wave 2: Mobile Visualization Recovery Validation Complete!');
    console.log('📊 Screenshots saved to: visual-diagnosis-screenshots/');
    console.log('   - event-cascade-flow-mobile-ENHANCED-375x667.png');
    console.log('   - narrative-timeline-mobile-ENHANCED-375x667.png'); 
    console.log('   - character-networks-mobile-CURRENT-375x667.png');
    console.log('   - dashboard-mobile-WAVE2-375x667.png');

  } catch (error) {
    console.error('❌ Validation failed:', error.message);
  } finally {
    await browser.close();
  }
}

validateWave2Visualizations().catch(console.error);