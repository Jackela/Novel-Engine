import { chromium } from 'playwright';

async function measureMobileHeight() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 375, height: 667 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
  });

  const page = await context.newPage();

  try {
    console.log('🔍 Navigating to dashboard...');
    await page.goto('http://localhost:3004');
    
    await page.waitForSelector('[data-testid="world-state-map"]', { timeout: 30000 });
    console.log('✅ Dashboard loaded successfully');
    await page.waitForTimeout(3000);

    // Measure total document height
    const documentHeight = await page.evaluate(() => document.body.scrollHeight);
    const viewportHeight = 667;
    const scrollRatio = (documentHeight / viewportHeight).toFixed(1);

    console.log('\n📏 Mobile Height Analysis:');
    console.log(`   Viewport Height: ${viewportHeight}px`);
    console.log(`   Document Height: ${documentHeight}px`);
    console.log(`   Scroll Ratio: ${scrollRatio}x viewport`);
    console.log(`   Target: <1.5x viewport (1000px)`);
    console.log(`   Status: ${documentHeight > 1000 ? '❌ EXCEEDS TARGET' : '✅ WITHIN TARGET'}`);

    // Measure individual component heights
    const components = [
      '[data-testid="world-state-map"]',
      '[data-testid="real-time-activity"]', 
      '[data-testid="performance-metrics"]',
      'text=Turn Pipeline',
      'text=Actions',
      'text=Character Networks',
      'text=Event Cascade Flow',
      'text=Narrative Arc Timeline',
      'text=Analytics'
    ];

    console.log('\n📊 Component Heights:');
    for (const selector of components) {
      try {
        const element = await page.locator(selector).first();
        const box = await element.boundingBox();
        if (box) {
          console.log(`   ${selector.replace('[data-testid="', '').replace('"]', '').replace('text=', '')}: ${box.height}px`);
        }
      } catch (e) {
        console.log(`   ${selector}: Not found or error`);
      }
    }

    return documentHeight;

  } catch (error) {
    console.error('❌ Measurement failed:', error.message);
  } finally {
    await browser.close();
  }
}

measureMobileHeight().catch(console.error);