const { chromium } = require('playwright');

/**
 * Mobile Quick Actions Component Validation Script
 * 
 * Purpose: Validate that the Quick Actions component fix successfully renders
 * buttons on mobile viewport (375x667px) after the height and layout fixes.
 */

async function validateMobileQuickActions() {
  console.log('🔍 Starting Mobile Quick Actions Validation...');
  
  const browser = await chromium.launch({
    headless: false, // Show browser for visual confirmation
  });
  
  const page = await browser.newPage();
  
  // Set mobile viewport
  await page.setViewportSize({ width: 375, height: 667 });
  
  try {
    // Navigate to dashboard
    console.log('📱 Navigating to dashboard at mobile viewport (375x667)...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle'
    });
    
    // Wait for dashboard to load
    await page.waitForTimeout(3000);
    
    // Find the Quick Actions component
    console.log('🎯 Locating Quick Actions component...');
    const quickActionsComponent = await page.locator('[data-testid="quick-actions"]');
    
    if (!await quickActionsComponent.isVisible()) {
      throw new Error('Quick Actions component not found or not visible');
    }
    
    // Capture full mobile dashboard screenshot
    console.log('📸 Capturing full mobile dashboard...');
    await page.screenshot({ 
      path: 'mobile-dashboard-after-fix.png',
      fullPage: true 
    });
    
    // Capture focused Quick Actions screenshot
    console.log('🔍 Capturing Quick Actions component specifically...');
    await quickActionsComponent.screenshot({ 
      path: 'quick-actions-mobile-after-fix.png' 
    });
    
    // Analyze the Quick Actions component structure
    const analysisResults = await analyzeQuickActionsComponent(page);
    
    // Generate validation report
    await generateValidationReport(analysisResults);
    
    console.log('✅ Mobile Quick Actions validation completed!');
    console.log('📄 Check validation report and screenshots for results.');
    
  } catch (error) {
    console.error('❌ Validation failed:', error.message);
  } finally {
    await browser.close();
  }
}

async function analyzeQuickActionsComponent(page) {
  console.log('🔬 Analyzing Quick Actions component structure...');
  
  const analysis = {
    timestamp: new Date().toISOString(),
    viewport: { width: 375, height: 667 },
    component_found: false,
    buttons_found: [],
    layout_measurements: {},
    visual_issues: [],
    success_indicators: []
  };
  
  try {
    // Check if component exists and is visible
    const quickActions = await page.locator('[data-testid="quick-actions"]');
    analysis.component_found = await quickActions.isVisible();
    
    if (analysis.component_found) {
      // Get component dimensions
      const boundingBox = await quickActions.boundingBox();
      analysis.layout_measurements = {
        width: boundingBox.width,
        height: boundingBox.height,
        x: boundingBox.x,
        y: boundingBox.y
      };
      
      // Check for action buttons
      const buttonSelectors = [
        '[data-testid="run-turn-button"]',
        'button[aria-label*="Stop"]',
        'button[aria-label*="Refresh"]', 
        'button[aria-label*="Save"]',
        'button[aria-label*="Settings"]'
      ];
      
      for (const selector of buttonSelectors) {
        try {
          const button = quickActions.locator(selector);
          if (await button.isVisible()) {
            const buttonBox = await button.boundingBox();
            analysis.buttons_found.push({
              selector,
              visible: true,
              dimensions: buttonBox
            });
            analysis.success_indicators.push(`Button found: ${selector}`);
          }
        } catch (e) {
          // Button not found with this selector, try alternative
        }
      }
      
      // Check for any buttons in the component (broader search)
      const allButtons = await quickActions.locator('button').all();
      const visibleButtons = [];
      
      for (let button of allButtons) {
        if (await button.isVisible()) {
          const text = await button.textContent();
          const ariaLabel = await button.getAttribute('aria-label');
          const boundingBox = await button.boundingBox();
          
          visibleButtons.push({
            text: text || '',
            ariaLabel: ariaLabel || '',
            dimensions: boundingBox,
            visible: true
          });
        }
      }
      
      analysis.buttons_found = [...analysis.buttons_found, ...visibleButtons];
      
      // Validate fix success criteria
      if (analysis.buttons_found.length === 0) {
        analysis.visual_issues.push('No buttons found in Quick Actions component');
      } else {
        analysis.success_indicators.push(`Found ${analysis.buttons_found.length} visible buttons`);
      }
      
      // Check if height is sufficient
      if (analysis.layout_measurements.height < 150) {
        analysis.visual_issues.push(`Component height may be too small: ${analysis.layout_measurements.height}px`);
      } else {
        analysis.success_indicators.push(`Adequate component height: ${analysis.layout_measurements.height}px`);
      }
      
      // Check for horizontal scrolling capability
      const hasOverflowX = await quickActions.evaluate(el => {
        const style = window.getComputedStyle(el.querySelector('[style*="overflow-x"], [style*="overflowX"]') || el);
        return style.overflowX === 'auto' || style.overflowX === 'scroll';
      });
      
      if (hasOverflowX) {
        analysis.success_indicators.push('Horizontal scrolling available for mobile');
      }
    
    } else {
      analysis.visual_issues.push('Quick Actions component not visible');
    }
    
  } catch (error) {
    analysis.visual_issues.push(`Analysis error: ${error.message}`);
  }
  
  return analysis;
}

async function generateValidationReport(analysis) {
  console.log('📊 Generating validation report...');
  
  const report = `# Mobile Quick Actions Fix Validation Report

## Test Overview
- **Date**: ${analysis.timestamp}
- **Viewport**: ${analysis.viewport.width}x${analysis.viewport.height}px (Mobile)
- **Component Found**: ${analysis.component_found ? '✅ Yes' : '❌ No'}

## Component Analysis

### Layout Measurements
- **Width**: ${analysis.layout_measurements.width || 'N/A'}px
- **Height**: ${analysis.layout_measurements.height || 'N/A'}px
- **Position**: (${analysis.layout_measurements.x || 'N/A'}, ${analysis.layout_measurements.y || 'N/A'})

### Button Analysis
**Buttons Found**: ${analysis.buttons_found.length}

${analysis.buttons_found.map((button, index) => `
**Button ${index + 1}:**
- Selector: ${button.selector || 'Generic button'}
- Text: "${button.text || 'N/A'}"
- Aria Label: "${button.ariaLabel || 'N/A'}"  
- Dimensions: ${button.dimensions ? `${button.dimensions.width}x${button.dimensions.height}px` : 'N/A'}
- Visible: ${button.visible ? '✅' : '❌'}
`).join('')}

## Validation Results

### ✅ Success Indicators
${analysis.success_indicators.map(indicator => `- ${indicator}`).join('\n')}

### ⚠️ Issues Identified  
${analysis.visual_issues.length > 0 ? analysis.visual_issues.map(issue => `- ${issue}`).join('\n') : '- None detected'}

## Fix Assessment

**Overall Status**: ${analysis.buttons_found.length > 0 && analysis.component_found ? '✅ FIX SUCCESSFUL' : '❌ FIX INCOMPLETE'}

${analysis.buttons_found.length > 0 && analysis.component_found ? 
`**Summary**: The Quick Actions mobile fix has been successful. The component now renders visible buttons on mobile viewport, resolving the critical P0 UX issue identified in the original diagnosis.` :
`**Summary**: The Quick Actions mobile fix requires additional work. The component is still not rendering buttons properly on mobile viewport.`}

## Visual Evidence

- \`mobile-dashboard-after-fix.png\` - Full mobile dashboard after fix
- \`quick-actions-mobile-after-fix.png\` - Focused Quick Actions component

## Comparison with Original Issue

**Before Fix**: Quick Actions component showed only title with completely empty content area  
**After Fix**: ${analysis.buttons_found.length > 0 ? `Component now shows ${analysis.buttons_found.length} visible action buttons` : 'Issue persists - no buttons visible'}

---

*Report generated by Mobile Quick Actions Validation Script*
`;
  
  const fs = require('fs');
  await fs.promises.writeFile('MOBILE_QUICKACTIONS_FIX_VALIDATION.md', report);
  
  console.log('📄 Validation report saved as MOBILE_QUICKACTIONS_FIX_VALIDATION.md');
}

// Run validation if script is executed directly
if (require.main === module) {
  validateMobileQuickActions();
}

module.exports = { validateMobileQuickActions };