import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Comprehensive Visual Diagnosis Screenshot Capture
 * Captures dashboard across responsive breakpoints for UX analysis
 */

const BREAKPOINTS = {
  desktop: { width: 1920, height: 1080, name: 'Desktop' },
  tablet: { width: 768, height: 1024, name: 'Tablet' },
  mobile: { width: 375, height: 667, name: 'Mobile' }
};

const BASE_URL = 'http://localhost:3001';
const SCREENSHOT_DIR = './visual-diagnosis-screenshots';

async function captureResponsiveScreenshots() {
  console.log('🎯 Starting Comprehensive Visual Diagnosis Screenshot Capture');
  
  // Ensure screenshot directory exists
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ 
    headless: true,
    args: ['--disable-web-security', '--disable-features=VizDisplayCompositor']
  });

  try {
    for (const [breakpointKey, config] of Object.entries(BREAKPOINTS)) {
      console.log(`📱 Capturing ${config.name} (${config.width}x${config.height})...`);
      
      const context = await browser.newContext({
        viewport: { width: config.width, height: config.height },
        deviceScaleFactor: 1,
        hasTouch: breakpointKey === 'mobile'
      });

      const page = await context.newPage();
      
      // Navigate to dashboard
      await page.goto(BASE_URL, { waitUntil: 'networkidle' });
      
      // Wait for dashboard to fully load
      await page.waitForSelector('[data-testid="dashboard-layout"]', { timeout: 30000 });
      await page.waitForTimeout(2000); // Allow animations to settle
      
      // Capture full page screenshot
      const screenshotPath = path.join(SCREENSHOT_DIR, `dashboard-${breakpointKey}-${config.width}x${config.height}.png`);
      await page.screenshot({ 
        path: screenshotPath, 
        fullPage: true,
        animations: 'disabled'
      });

      // Capture component-specific screenshots for detailed analysis
      const components = [
        { selector: '[data-testid="world-state-map"]', name: 'world-state-map' },
        { selector: '[data-testid="real-time-activity"]', name: 'real-time-activity' },
        { selector: '[data-testid="performance-metrics"]', name: 'performance-metrics' },
        { selector: '[data-testid="turn-pipeline-status"]', name: 'turn-pipeline-status' },
        { selector: '[data-testid="quick-actions"]', name: 'quick-actions' }
      ];

      for (const component of components) {
        try {
          const element = await page.locator(component.selector).first();
          if (await element.isVisible()) {
            const componentPath = path.join(SCREENSHOT_DIR, `${component.name}-${breakpointKey}-${config.width}x${config.height}.png`);
            await element.screenshot({ 
              path: componentPath,
              animations: 'disabled'
            });
          }
        } catch (error) {
          console.log(`⚠️  Component ${component.name} not found at ${breakpointKey}`);
        }
      }

      // Capture viewport-specific metadata
      const viewportInfo = await page.evaluate(() => ({
        scrollHeight: document.documentElement.scrollHeight,
        clientHeight: document.documentElement.clientHeight,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        components: Array.from(document.querySelectorAll('[data-testid]')).map(el => ({
          testId: el.getAttribute('data-testid'),
          visible: el.offsetWidth > 0 && el.offsetHeight > 0,
          bounds: el.getBoundingClientRect(),
          computedStyle: {
            display: window.getComputedStyle(el).display,
            visibility: window.getComputedStyle(el).visibility,
            overflow: window.getComputedStyle(el).overflow
          }
        }))
      }));

      // Save viewport analysis data
      const metadataPath = path.join(SCREENSHOT_DIR, `metadata-${breakpointKey}.json`);
      fs.writeFileSync(metadataPath, JSON.stringify({
        breakpoint: breakpointKey,
        viewport: config,
        timestamp: new Date().toISOString(),
        analysis: viewportInfo
      }, null, 2));

      await context.close();
      console.log(`✅ ${config.name} capture complete`);
    }

    console.log('\n🎉 All responsive screenshots captured successfully!');
    console.log(`📁 Screenshots saved to: ${path.resolve(SCREENSHOT_DIR)}`);
    
    // Generate capture summary
    const summary = {
      captureTime: new Date().toISOString(),
      breakpoints: Object.keys(BREAKPOINTS),
      totalScreenshots: fs.readdirSync(SCREENSHOT_DIR).filter(f => f.endsWith('.png')).length,
      baseUrl: BASE_URL,
      captureDirectory: path.resolve(SCREENSHOT_DIR)
    };
    
    fs.writeFileSync(path.join(SCREENSHOT_DIR, 'capture-summary.json'), JSON.stringify(summary, null, 2));
    
    return summary;

  } catch (error) {
    console.error('❌ Screenshot capture failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

// Execute if run directly
if (process.argv[1] === __filename) {
  captureResponsiveScreenshots()
    .then(summary => {
      console.log('\n📊 Capture Summary:', summary);
      process.exit(0);
    })
    .catch(error => {
      console.error('💥 Capture failed:', error);
      process.exit(1);
    });
}

export { captureResponsiveScreenshots, BREAKPOINTS, SCREENSHOT_DIR };