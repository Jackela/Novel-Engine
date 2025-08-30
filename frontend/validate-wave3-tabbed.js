import { chromium } from 'playwright';

async function validateWave3Tabbed() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 375, height: 667 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
  });

  const page = await context.newPage();

  try {
    console.log('🔍 Navigating to tabbed dashboard...');
    await page.goto('http://localhost:3004');
    
    await page.waitForSelector('[data-testid="world-state-map"]', { timeout: 30000 });
    console.log('✅ Tabbed dashboard loaded successfully');
    await page.waitForTimeout(3000);

    // Measure new mobile height with tabbed interface
    const documentHeight = await page.evaluate(() => document.body.scrollHeight);
    const viewportHeight = 667;
    const scrollRatio = (documentHeight / viewportHeight).toFixed(1);
    
    console.log('\n📏 Wave 3 Tabbed Interface Results:');
    console.log(`   Viewport Height: ${viewportHeight}px`);
    console.log(`   New Document Height: ${documentHeight}px`);
    console.log(`   New Scroll Ratio: ${scrollRatio}x viewport`);
    console.log(`   Target: <1.5x viewport (1000px)`);
    console.log(`   Reduction from Original 2215px: ${((2215 - documentHeight) / 2215 * 100).toFixed(1)}%`);
    console.log(`   Status: ${documentHeight > 1000 ? '❌ STILL EXCEEDS TARGET' : '✅ TARGET ACHIEVED'}`);

    // Capture tabbed layout screenshots
    await page.screenshot({ 
      path: 'visual-diagnosis-screenshots/dashboard-mobile-TABBED-overview-375x667.png',
      fullPage: false // Just viewport
    });
    console.log('✅ Tabbed Overview screenshot captured');

    // Test tab switching
    const tabs = ['Activity', 'Story', 'Analytics'];
    for (let i = 0; i < tabs.length; i++) {
      try {
        const tabName = tabs[i];
        const tabSelector = `[role="tab"]:has-text("${tabName}")`;
        
        if (await page.locator(tabSelector).isVisible()) {
          await page.locator(tabSelector).click();
          await page.waitForTimeout(1000);
          
          await page.screenshot({ 
            path: `visual-diagnosis-screenshots/dashboard-mobile-TABBED-${tabName.toLowerCase()}-375x667.png`,
            fullPage: false
          });
          console.log(`✅ ${tabName} tab screenshot captured`);
        }
      } catch (e) {
        console.log(`ℹ️  ${tabs[i]} tab test skipped`);
      }
    }

    // Measure height on different tabs
    for (let i = 1; i < 4; i++) {
      try {
        await page.evaluate((tabIndex) => {
          const tabs = document.querySelectorAll('[role="tab"]');
          if (tabs[tabIndex]) tabs[tabIndex].click();
        }, i);
        
        await page.waitForTimeout(500);
        const tabHeight = await page.evaluate(() => document.body.scrollHeight);
        console.log(`   Tab ${i+1} Height: ${tabHeight}px`);
      } catch (e) {
        console.log(`   Tab ${i+1}: Unable to measure`);
      }
    }

    console.log('\n🎯 Wave 3: Mobile Tabbed Interface Validation Complete!');
    console.log('📊 Screenshots saved to: visual-diagnosis-screenshots/');
    console.log('   - dashboard-mobile-TABBED-overview-375x667.png');
    console.log('   - dashboard-mobile-TABBED-activity-375x667.png'); 
    console.log('   - dashboard-mobile-TABBED-story-375x667.png');
    console.log('   - dashboard-mobile-TABBED-analytics-375x667.png');

    return {
      height: documentHeight,
      targetMet: documentHeight <= 1000,
      reductionPercentage: ((2215 - documentHeight) / 2215 * 100).toFixed(1)
    };

  } catch (error) {
    console.error('❌ Wave 3 tabbed validation failed:', error.message);
    return null;
  } finally {
    await browser.close();
  }
}

validateWave3Tabbed().catch(console.error);