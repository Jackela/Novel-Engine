#!/usr/bin/env node

/**
 * Desktop Verification Screenshot
 * Captures desktop screenshot to ensure functionality remains intact
 */

const { chromium } = require('playwright');

async function captureDesktopVerification() {
  let browser;
  
  try {
    console.log('🖥️  Starting desktop verification screenshot...');
    
    browser = await chromium.launch({ 
      headless: false,
      slowMo: 200 
    });
    
    const page = await browser.newPage();
    
    // Set desktop viewport 
    await page.setViewportSize({ width: 1440, height: 900 });
    
    console.log('🧭 Navigating to dashboard at desktop viewport...');
    await page.goto('http://localhost:3002', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    await page.waitForTimeout(3000);
    
    // Take Quick Actions component screenshot
    const timestamp = Date.now();
    
    try {
      console.log('📸 Capturing desktop Quick Actions component...');
      
      const quickActionsSelector = '[data-testid="quick-actions"]';
      await page.waitForSelector(quickActionsSelector, { timeout: 10000 });
      
      const quickActionsElement = await page.locator(quickActionsSelector);
      const desktopPath = `./desktop-verification-quick-actions-${timestamp}.png`;
      
      await quickActionsElement.screenshot({ path: desktopPath });
      
      console.log(`✅ Desktop Quick Actions screenshot: ${desktopPath}`);
      
      // Check button layout orientation
      const buttonCount = await page.locator('[data-testid="quick-actions"] button').count();
      console.log(`🔍 Found ${buttonCount} action buttons in desktop view`);
      
      // Get component dimensions
      const boundingBox = await quickActionsElement.boundingBox();
      if (boundingBox) {
        console.log(`📏 Desktop Quick Actions dimensions: ${boundingBox.width}x${boundingBox.height}px`);
      }
      
    } catch (error) {
      console.error('❌ Desktop verification failed:', error.message);
    }
    
  } catch (error) {
    console.error('❌ Desktop verification failed:', error);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

if (require.main === module) {
  captureDesktopVerification().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}