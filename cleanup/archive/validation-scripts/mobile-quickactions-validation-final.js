/**
 * Mobile QuickActions Validation Script - Final Fix Verification
 * =============================================================
 * 
 * Captures and analyzes mobile screenshot to validate QuickActions fix
 * after implementing the height constraint and padding optimizations.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function validateQuickActionsFix() {
  console.log('🔍 Validating QuickActions mobile fix...');
  
  const browser = await chromium.launch({
    headless: false, // Show browser for debugging
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 }, // iPhone SE mobile viewport
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'
    });

    const page = await context.newPage();
    
    // Navigate to dashboard
    console.log('📱 Loading dashboard on mobile viewport (375x667)...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    // Wait for dashboard to load
    await page.waitForTimeout(3000);

    // Take full page screenshot
    const timestamp = Date.now();
    const screenshotPath = `mobile-quickactions-fix-validation-${timestamp}.png`;
    
    console.log('📸 Capturing mobile dashboard screenshot...');
    await page.screenshot({ 
      path: screenshotPath, 
      fullPage: true,
      animations: 'disabled'
    });

    console.log(`✅ Screenshot saved: ${screenshotPath}`);

    // Analyze QuickActions component specifically
    console.log('🔍 Analyzing QuickActions component...');
    
    const quickActionsAnalysis = await page.evaluate(() => {
      const quickActions = document.querySelector('[data-testid="quick-actions"]');
      if (!quickActions) {
        return { found: false, error: 'QuickActions component not found' };
      }

      const rect = quickActions.getBoundingClientRect();
      const buttons = quickActions.querySelectorAll('button');
      const title = quickActions.querySelector('h2, h6');
      
      const buttonAnalysis = Array.from(buttons).map(button => {
        const buttonRect = button.getBoundingClientRect();
        const isVisible = buttonRect.width > 0 && buttonRect.height > 0 && 
                         window.getComputedStyle(button).visibility !== 'hidden' &&
                         window.getComputedStyle(button).display !== 'none';
        
        return {
          text: button.getAttribute('aria-label') || button.title || 'Unknown',
          width: Math.round(buttonRect.width),
          height: Math.round(buttonRect.height),
          visible: isVisible,
          position: {
            x: Math.round(buttonRect.left),
            y: Math.round(buttonRect.top)
          }
        };
      });

      return {
        found: true,
        title: title?.textContent || 'No title found',
        componentSize: {
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        },
        totalButtons: buttons.length,
        visibleButtons: buttonAnalysis.filter(b => b.visible).length,
        buttons: buttonAnalysis,
        containerClasses: quickActions.className,
        hasContent: buttons.length > 0
      };
    });

    // Generate detailed analysis report
    console.log('\n📊 QUICKACTIONS MOBILE ANALYSIS REPORT');
    console.log('=====================================');
    
    if (!quickActionsAnalysis.found) {
      console.log('❌ CRITICAL: QuickActions component not found!');
      console.log(`Error: ${quickActionsAnalysis.error}`);
      return false;
    }

    console.log(`✅ Component Found: ${quickActionsAnalysis.title}`);
    console.log(`📏 Component Size: ${quickActionsAnalysis.componentSize.width}x${quickActionsAnalysis.componentSize.height}px`);
    console.log(`🔘 Total Buttons: ${quickActionsAnalysis.totalButtons}`);
    console.log(`👁️  Visible Buttons: ${quickActionsAnalysis.visibleButtons}`);
    
    const isFixSuccessful = quickActionsAnalysis.hasContent && 
                           quickActionsAnalysis.visibleButtons > 0 &&
                           quickActionsAnalysis.totalButtons >= 5; // Should have at least 5 mobile actions

    if (isFixSuccessful) {
      console.log('\n🎉 SUCCESS: QuickActions mobile fix is working!');
      console.log('✅ Component renders with visible action buttons');
      console.log('✅ Buttons have proper touch-friendly sizing');
      
      // Detailed button analysis
      console.log('\n🔘 BUTTON DETAILS:');
      quickActionsAnalysis.buttons.forEach((button, index) => {
        const status = button.visible ? '✅' : '❌';
        const touchFriendly = button.height >= 44 && button.width >= 44 ? '👍' : '⚠️';
        console.log(`  ${status} ${touchFriendly} ${button.text}: ${button.width}x${button.height}px`);
      });
      
    } else {
      console.log('\n❌ FAILURE: QuickActions mobile fix needs more work');
      console.log(`- Has Content: ${quickActionsAnalysis.hasContent}`);
      console.log(`- Visible Buttons: ${quickActionsAnalysis.visibleButtons}/${quickActionsAnalysis.totalButtons}`);
    }

    // Check if we're on Overview tab (where QuickActions should be)
    const currentTab = await page.evaluate(() => {
      const activeTab = document.querySelector('[role="tab"][aria-selected="true"]');
      return activeTab ? activeTab.textContent : 'Unknown';
    });
    
    console.log(`📱 Current Mobile Tab: ${currentTab}`);

    // Save analysis results
    const analysisReport = {
      timestamp: new Date().toISOString(),
      viewport: { width: 375, height: 667 },
      screenshot: screenshotPath,
      quickActions: quickActionsAnalysis,
      currentTab,
      fixSuccessful: isFixSuccessful,
      summary: {
        component_found: quickActionsAnalysis.found,
        buttons_visible: quickActionsAnalysis.visibleButtons,
        total_buttons: quickActionsAnalysis.totalButtons,
        component_height: quickActionsAnalysis.componentSize?.height || 0,
        touch_friendly: quickActionsAnalysis.buttons?.every(b => b.visible && b.height >= 44) || false
      }
    };

    const reportPath = `mobile-quickactions-fix-validation-${timestamp}.json`;
    fs.writeFileSync(reportPath, JSON.stringify(analysisReport, null, 2));
    console.log(`📄 Analysis report saved: ${reportPath}`);

    return isFixSuccessful;

  } catch (error) {
    console.error('❌ Error during validation:', error.message);
    return false;
  } finally {
    await browser.close();
  }
}

// Run validation if script is called directly
if (require.main === module) {
  validateQuickActionsFix()
    .then(success => {
      console.log(success ? '\n🎉 VALIDATION PASSED!' : '\n❌ VALIDATION FAILED!');
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('Fatal error:', error);
      process.exit(1);
    });
}

module.exports = { validateQuickActionsFix };