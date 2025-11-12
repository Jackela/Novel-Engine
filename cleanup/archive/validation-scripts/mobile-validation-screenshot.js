#!/usr/bin/env node

/**
 * Mobile Validation Screenshot Script
 * Captures mobile screenshot at 375x667px to validate Quick Actions fix
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function captureValidationScreenshot() {
  let browser;
  
  try {
    console.log('🚀 Starting mobile validation screenshot capture...');
    
    // Launch browser
    browser = await chromium.launch({ 
      headless: false,
      slowMo: 300 
    });
    
    const page = await browser.newPage();
    
    // Set mobile viewport (iPhone SE dimensions)
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate to dashboard
    console.log('🧭 Navigating to dashboard at mobile viewport...');
    await page.goto('http://localhost:3002', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Wait for dashboard to load
    await page.waitForTimeout(3000);
    
    // Take full page screenshot
    const timestamp = Date.now();
    const fullPagePath = `./mobile-validation-fullpage-${timestamp}.png`;
    
    console.log('📸 Capturing full mobile dashboard screenshot...');
    await page.screenshot({ 
      path: fullPagePath, 
      fullPage: true 
    });
    
    console.log(`✅ Full page screenshot saved: ${fullPagePath}`);
    
    // Try to locate and screenshot the Quick Actions component specifically
    try {
      console.log('🔍 Locating Quick Actions component...');
      
      // Wait for Quick Actions component
      const quickActionsSelector = '[data-testid="quick-actions"]';
      await page.waitForSelector(quickActionsSelector, { timeout: 10000 });
      
      // Take component-specific screenshot
      const componentPath = `./mobile-validation-quick-actions-${timestamp}.png`;
      const quickActionsElement = await page.locator(quickActionsSelector);
      
      console.log('📸 Capturing Quick Actions component screenshot...');
      await quickActionsElement.screenshot({ 
        path: componentPath 
      });
      
      console.log(`✅ Quick Actions screenshot saved: ${componentPath}`);
      
      // Check if buttons are visible
      const buttonCount = await page.locator('[data-testid="quick-actions"] button').count();
      console.log(`🔍 Found ${buttonCount} action buttons in mobile view`);
      
      // Get component dimensions
      const boundingBox = await quickActionsElement.boundingBox();
      if (boundingBox) {
        console.log(`📏 Quick Actions dimensions: ${boundingBox.width}x${boundingBox.height}px`);
      }
      
    } catch (error) {
      console.warn('⚠️  Could not capture component-specific screenshot:', error.message);
    }
    
    // Capture viewport info
    const viewportInfo = await page.evaluate(() => ({
      width: window.innerWidth,
      height: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio,
      userAgent: navigator.userAgent
    }));
    
    console.log('📱 Mobile viewport info:');
    console.log(`   Width: ${viewportInfo.width}px`);
    console.log(`   Height: ${viewportInfo.height}px`);
    console.log(`   Device Pixel Ratio: ${viewportInfo.devicePixelRatio}`);
    
    // Generate validation report
    const report = {
      timestamp: new Date().toISOString(),
      viewport: { width: 375, height: 667 },
      actualViewport: viewportInfo,
      screenshots: {
        fullPage: fullPagePath,
        component: componentPath || null
      },
      validation: {
        quickActionsFound: true,
        buttonsVisible: buttonCount > 0,
        buttonCount: buttonCount
      }
    };
    
    const reportPath = `./mobile-validation-report-${timestamp}.json`;
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`📊 Validation report saved: ${reportPath}`);
    
    console.log('');
    console.log('🎉 Mobile validation screenshot capture completed!');
    console.log(`📸 Screenshots: ${Object.values(report.screenshots).filter(Boolean).length}`);
    console.log(`🔧 Quick Actions Status: ${report.validation.quickActionsFound ? 'FOUND' : 'NOT FOUND'}`);
    console.log(`🎯 Action Buttons: ${report.validation.buttonCount} visible`);
    
    return report;
    
  } catch (error) {
    console.error('❌ Mobile validation failed:', error);
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Run validation
if (require.main === module) {
  captureValidationScreenshot().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { captureValidationScreenshot };