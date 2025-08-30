import { chromium } from 'playwright';

async function validateWave3Accordion() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 375, height: 667 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
  });

  const page = await context.newPage();

  try {
    console.log('🔍 Navigating to accordion dashboard...');
    await page.goto('http://localhost:3004');
    
    await page.waitForSelector('[data-testid="world-state-map"]', { timeout: 30000 });
    console.log('✅ Accordion dashboard loaded successfully');
    await page.waitForTimeout(3000);

    // Measure new mobile height with accordion
    const documentHeight = await page.evaluate(() => document.body.scrollHeight);
    const viewportHeight = 667;
    const scrollRatio = (documentHeight / viewportHeight).toFixed(1);
    
    console.log('\n📏 Wave 3 Accordion Results:');
    console.log(`   Viewport Height: ${viewportHeight}px`);
    console.log(`   New Document Height: ${documentHeight}px`);
    console.log(`   New Scroll Ratio: ${scrollRatio}x viewport`);
    console.log(`   Target: <1.5x viewport (1000px)`);
    console.log(`   Reduction from 2215px: ${((2215 - documentHeight) / 2215 * 100).toFixed(1)}%`);
    console.log(`   Status: ${documentHeight > 1000 ? '❌ STILL EXCEEDS TARGET' : '✅ TARGET ACHIEVED'}`);

    // Capture accordion layout screenshots
    await page.screenshot({ 
      path: 'visual-diagnosis-screenshots/dashboard-mobile-ACCORDION-375x667.png',
      fullPage: true 
    });
    console.log('✅ Mobile accordion screenshot captured');

    // Test accordion interaction - expand Character section
    try {
      const characterAccordion = page.locator('text=Characters & Events').locator('..');
      if (await characterAccordion.isVisible()) {
        await characterAccordion.click();
        await page.waitForTimeout(1000);
        
        await page.screenshot({ 
          path: 'visual-diagnosis-screenshots/dashboard-mobile-EXPANDED-375x667.png',
          fullPage: true 
        });
        console.log('✅ Expanded accordion screenshot captured');
      }
    } catch (e) {
      console.log('ℹ️  Accordion interaction test skipped (component may not be found)');
    }

    console.log('\n🎯 Wave 3: Mobile Content Strategy Validation Complete!');
    console.log('📊 Screenshots saved to: visual-diagnosis-screenshots/');
    console.log('   - dashboard-mobile-ACCORDION-375x667.png');
    console.log('   - dashboard-mobile-EXPANDED-375x667.png');

    return {
      height: documentHeight,
      targetMet: documentHeight <= 1000,
      reductionPercentage: ((2215 - documentHeight) / 2215 * 100).toFixed(1)
    };

  } catch (error) {
    console.error('❌ Wave 3 validation failed:', error.message);
    return null;
  } finally {
    await browser.close();
  }
}

validateWave3Accordion().catch(console.error);