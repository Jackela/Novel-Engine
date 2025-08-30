import { chromium } from 'playwright';
import fs from 'fs';

async function captureDashboard() {
  console.log('🚀 Capturing dashboard implementation...');
  
  const browser = await chromium.launch({ 
    headless: true
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  
  const page = await context.newPage();
  
  try {
    // Navigate to the preview server
    console.log('Navigating to preview server...');
    await page.goto('http://localhost:4173', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Wait for the dashboard to render
    await page.waitForTimeout(3000);
    
    // Take screenshot
    const timestamp = Date.now();
    const screenshotPath = `screenshots/dashboard-test-${timestamp}.png`;
    await page.screenshot({ 
      path: screenshotPath,
      fullPage: true 
    });
    
    console.log(`✅ Screenshot saved: ${screenshotPath}`);
    
    // Check if the dashboard is rendering by looking for key elements
    const dashboardTitle = await page.locator('h1').first().textContent().catch(() => null);
    const tiles = await page.locator('.bento-tile').count().catch(() => 0);
    
    console.log('\n📊 Dashboard Status:');
    console.log(`- Title: ${dashboardTitle || 'Not found'}`);
    console.log(`- Bento tiles found: ${tiles}`);
    
    // Check for any console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error('Browser console error:', msg.text());
      }
    });
    
    // Get page content for debugging
    const bodyContent = await page.$eval('body', el => {
      return {
        hasContent: el.innerHTML.length > 100,
        backgroundColor: window.getComputedStyle(el).backgroundColor,
        firstElementTag: el.firstElementChild ? el.firstElementChild.tagName : 'none'
      };
    });
    
    console.log('\n🔍 Page Analysis:');
    console.log(`- Has content: ${bodyContent.hasContent}`);
    console.log(`- Background color: ${bodyContent.backgroundColor}`);
    console.log(`- First element: ${bodyContent.firstElementTag}`);
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
}

captureDashboard();