import { chromium } from 'playwright';
import fs from 'fs';

async function captureLiveDashboard() {
  console.log('Capturing live dashboard...');
  
  const browser = await chromium.launch({ 
    headless: false, // Show browser for debugging
    devtools: true
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  
  const page = await context.newPage();
  
  // Log console messages for debugging
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  try {
    console.log('Navigating to dashboard...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Wait for the dashboard to render
    console.log('Waiting for dashboard to load...');
    await page.waitForSelector('.emergent-dashboard', { timeout: 10000 }).catch(() => {
      console.log('Dashboard selector not found, checking for other elements...');
    });
    
    // Additional wait to ensure everything is rendered
    await page.waitForTimeout(3000);
    
    // Take screenshot
    const timestamp = Date.now();
    const screenshotPath = `screenshots/live-dashboard-${timestamp}.png`;
    await page.screenshot({ 
      path: screenshotPath,
      fullPage: true 
    });
    
    console.log(`✅ Screenshot saved: ${screenshotPath}`);
    
    // Check page content
    const content = await page.content();
    if (content.includes('emergent-dashboard')) {
      console.log('✅ Dashboard component found in DOM');
    } else if (content.includes('error')) {
      console.log('❌ Error found in page');
    }
    
    // Keep browser open for manual inspection
    console.log('\n📋 Browser will stay open for inspection.');
    console.log('Close the browser window when done.');
    
    // Wait for user to close browser
    await page.waitForTimeout(60000);
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
}

captureLiveDashboard();