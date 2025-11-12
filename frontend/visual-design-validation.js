/**
 * Visual Design Validation Script
 * Comprehensive validation of the refactored UI against design specifications
 * Tests desktop and mobile viewports for compliance with UI_VISUAL_DESIGN_SPEC.md
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

async function validateVisualDesign() {
  console.log('🎨 Starting Visual Design Validation...\n');
  
  const browser = await chromium.launch({ 
    headless: false, // Show browser to see the results
    slowMo: 1000 // Slow down for visual inspection
  });
  
  const context = await browser.newContext({
    ignoreHTTPSErrors: true
  });

  // Test Results Storage
  const results = {
    timestamp: new Date().toISOString(),
    testType: 'Visual Design Validation',
    desktop: {},
    mobile: {},
    compliance: {},
    screenshots: []
  };

  try {
    // ===============================================
    // DESKTOP VIEWPORT VALIDATION
    // ===============================================
    console.log('🖥️ Testing Desktop Viewport (1920x1080)...');
    
    const desktopPage = await context.newPage();
    await desktopPage.setViewportSize({ width: 1920, height: 1080 });
    
    // Navigate to the dashboard
    await desktopPage.goto('http://localhost:3002/dashboard', { 
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Wait for components to load
    await desktopPage.waitForTimeout(2000);

    // Take desktop screenshot
    const desktopScreenshot = `desktop-design-validation-${Date.now()}.png`;
    await desktopPage.screenshot({
      path: desktopScreenshot,
      fullPage: true
    });
    results.screenshots.push({ viewport: 'desktop', file: desktopScreenshot });
    console.log(`📸 Desktop screenshot saved: ${desktopScreenshot}`);

    // Validate Color Palette Implementation
    console.log('🎨 Validating Color Palette...');
    
    const colorValidation = await desktopPage.evaluate(() => {
      const computedStyles = getComputedStyle(document.documentElement);
      const bodyStyles = getComputedStyle(document.body);
      
      return {
        // Background colors
        primaryBg: bodyStyles.backgroundColor,
        
        // Check if CSS custom properties are available
        customProps: {
          colorPrimary: computedStyles.getPropertyValue('--color-primary'),
          colorSecondary: computedStyles.getPropertyValue('--color-secondary'),
          colorBgPrimary: computedStyles.getPropertyValue('--color-bg-primary'),
          colorBgSecondary: computedStyles.getPropertyValue('--color-bg-secondary'),
          colorTextPrimary: computedStyles.getPropertyValue('--color-text-primary'),
          fontPrimary: computedStyles.getPropertyValue('--font-primary')
        }
      };
    });

    results.desktop.colorValidation = colorValidation;
    console.log('✅ Color palette validation completed');

    // Validate Typography Implementation
    console.log('📝 Validating Typography System...');
    
    const typographyValidation = await desktopPage.evaluate(() => {
      // Find headings and text elements
      const h1 = document.querySelector('h1');
      const h2 = document.querySelector('h2');
      const h3 = document.querySelector('h3');
      const body = document.querySelector('p, body');
      
      return {
        h1: h1 ? {
          fontSize: getComputedStyle(h1).fontSize,
          fontFamily: getComputedStyle(h1).fontFamily,
          fontWeight: getComputedStyle(h1).fontWeight,
          color: getComputedStyle(h1).color
        } : null,
        h2: h2 ? {
          fontSize: getComputedStyle(h2).fontSize,
          fontFamily: getComputedStyle(h2).fontFamily,
          fontWeight: getComputedStyle(h2).fontWeight,
          color: getComputedStyle(h2).color
        } : null,
        h3: h3 ? {
          fontSize: getComputedStyle(h3).fontSize,
          fontFamily: getComputedStyle(h3).fontFamily,
          fontWeight: getComputedStyle(h3).fontWeight,
          color: getComputedStyle(h3).color
        } : null,
        body: body ? {
          fontSize: getComputedStyle(body).fontSize,
          fontFamily: getComputedStyle(body).fontFamily,
          fontWeight: getComputedStyle(body).fontWeight,
          color: getComputedStyle(body).color
        } : null
      };
    });

    results.desktop.typographyValidation = typographyValidation;
    console.log('✅ Typography validation completed');

    // Validate Bento Grid Layout
    console.log('📐 Validating Bento Grid Layout...');
    
    const layoutValidation = await desktopPage.evaluate(() => {
      const gridContainer = document.querySelector('[class*="GridContainer"], [class*="bento-grid"], .MuiGrid-container');
      
      if (gridContainer) {
        const styles = getComputedStyle(gridContainer);
        return {
          display: styles.display,
          gridTemplateColumns: styles.gridTemplateColumns,
          gap: styles.gap,
          maxWidth: styles.maxWidth,
          padding: styles.padding,
          margin: styles.margin
        };
      }
      
      return { error: 'Grid container not found' };
    });

    results.desktop.layoutValidation = layoutValidation;
    console.log('✅ Layout validation completed');

    // Validate Component Styling
    console.log('🧩 Validating Component Styling...');
    
    const componentValidation = await desktopPage.evaluate(() => {
      // Find dashboard components
      const tiles = document.querySelectorAll('[data-testid*="tile"], [class*="tile"], .MuiPaper-root');
      const buttons = document.querySelectorAll('button');
      const chips = document.querySelectorAll('.MuiChip-root');
      
      return {
        tileCount: tiles.length,
        tiles: Array.from(tiles).slice(0, 3).map(tile => ({
          backgroundColor: getComputedStyle(tile).backgroundColor,
          borderRadius: getComputedStyle(tile).borderRadius,
          border: getComputedStyle(tile).border,
          boxShadow: getComputedStyle(tile).boxShadow
        })),
        buttonCount: buttons.length,
        buttons: Array.from(buttons).slice(0, 2).map(button => ({
          backgroundColor: getComputedStyle(button).backgroundColor,
          color: getComputedStyle(button).color,
          borderRadius: getComputedStyle(button).borderRadius,
          fontFamily: getComputedStyle(button).fontFamily
        })),
        chipCount: chips.length,
        chips: Array.from(chips).slice(0, 2).map(chip => ({
          backgroundColor: getComputedStyle(chip).backgroundColor,
          color: getComputedStyle(chip).color,
          borderRadius: getComputedStyle(chip).borderRadius,
          fontSize: getComputedStyle(chip).fontSize
        }))
      };
    });

    results.desktop.componentValidation = componentValidation;
    console.log('✅ Component styling validation completed');

    // ===============================================
    // MOBILE VIEWPORT VALIDATION
    // ===============================================
    console.log('\n📱 Testing Mobile Viewport (390x844)...');
    
    const mobilePage = await context.newPage();
    await mobilePage.setViewportSize({ width: 390, height: 844 });
    
    await mobilePage.goto('http://localhost:3002/dashboard', { 
      waitUntil: 'networkidle',
      timeout: 30000
    });

    await mobilePage.waitForTimeout(2000);

    // Take mobile screenshot
    const mobileScreenshot = `mobile-design-validation-${Date.now()}.png`;
    await mobilePage.screenshot({
      path: mobileScreenshot,
      fullPage: true
    });
    results.screenshots.push({ viewport: 'mobile', file: mobileScreenshot });
    console.log(`📸 Mobile screenshot saved: ${mobileScreenshot}`);

    // Mobile layout validation
    const mobileLayoutValidation = await mobilePage.evaluate(() => {
      const gridContainer = document.querySelector('[class*="GridContainer"], [class*="bento-grid"], .MuiGrid-container');
      
      if (gridContainer) {
        const styles = getComputedStyle(gridContainer);
        return {
          display: styles.display,
          gridTemplateColumns: styles.gridTemplateColumns,
          gap: styles.gap,
          padding: styles.padding
        };
      }
      
      return { error: 'Grid container not found' };
    });

    results.mobile.layoutValidation = mobileLayoutValidation;
    console.log('✅ Mobile layout validation completed');

    // Mobile responsive validation
    const mobileResponsiveValidation = await mobilePage.evaluate(() => {
      const tiles = document.querySelectorAll('[data-testid*="tile"], [class*="tile"], .MuiPaper-root');
      
      return {
        tileCount: tiles.length,
        tiles: Array.from(tiles).slice(0, 2).map(tile => ({
          width: getComputedStyle(tile).width,
          padding: getComputedStyle(tile).padding,
          margin: getComputedStyle(tile).margin
        }))
      };
    });

    results.mobile.responsiveValidation = mobileResponsiveValidation;

    // ===============================================
    // COMPLIANCE ANALYSIS
    // ===============================================
    console.log('\n🎯 Analyzing Design Compliance...');
    
    // Check for compliance with design specifications
    const compliance = {
      colorPalette: {
        primary: colorValidation.customProps.colorPrimary?.trim() === '#6366f1',
        secondary: colorValidation.customProps.colorSecondary?.trim() === '#8b5cf6',
        bgPrimary: colorValidation.customProps.colorBgPrimary?.trim() === '#0a0a0b',
        textPrimary: colorValidation.customProps.colorTextPrimary?.trim() === '#f0f0f2'
      },
      typography: {
        fontFamily: colorValidation.customProps.fontPrimary?.includes('Inter'),
        h1Present: !!typographyValidation.h1,
        bodyTextPresent: !!typographyValidation.body
      },
      layout: {
        gridImplemented: layoutValidation.display === 'grid',
        responsiveGaps: mobileLayoutValidation.gap !== layoutValidation.gap
      },
      components: {
        tilesStyled: componentValidation.tileCount > 0,
        buttonsStyled: componentValidation.buttonCount > 0,
        chipsStyled: componentValidation.chipCount > 0
      }
    };

    results.compliance = compliance;

    // Calculate compliance score
    const complianceScores = Object.values(compliance).map(category => 
      Object.values(category).filter(Boolean).length / Object.values(category).length
    );
    const overallCompliance = complianceScores.reduce((a, b) => a + b) / complianceScores.length;
    
    results.overallComplianceScore = Math.round(overallCompliance * 100);
    console.log(`📊 Overall Compliance Score: ${results.overallComplianceScore}%`);

  } catch (error) {
    console.error('❌ Validation error:', error.message);
    results.error = error.message;
  }

  // Save results to file
  const reportFile = `visual-design-validation-report-${Date.now()}.json`;
  fs.writeFileSync(reportFile, JSON.stringify(results, null, 2));
  console.log(`📋 Validation report saved: ${reportFile}`);

  // ===============================================
  // SUMMARY REPORT
  // ===============================================
  console.log('\n' + '='.repeat(60));
  console.log('🎨 VISUAL DESIGN VALIDATION SUMMARY');
  console.log('='.repeat(60));
  
  console.log(`📊 Overall Compliance: ${results.overallComplianceScore}%`);
  console.log(`🖥️  Desktop Screenshots: ${results.screenshots.filter(s => s.viewport === 'desktop').length}`);
  console.log(`📱 Mobile Screenshots: ${results.screenshots.filter(s => s.viewport === 'mobile').length}`);
  
  if (results.compliance) {
    console.log('\n🎨 Color Palette Compliance:');
    Object.entries(results.compliance.colorPalette).forEach(([key, value]) => {
      console.log(`  ${value ? '✅' : '❌'} ${key}`);
    });
    
    console.log('\n📝 Typography Compliance:');
    Object.entries(results.compliance.typography).forEach(([key, value]) => {
      console.log(`  ${value ? '✅' : '❌'} ${key}`);
    });
    
    console.log('\n📐 Layout Compliance:');
    Object.entries(results.compliance.layout).forEach(([key, value]) => {
      console.log(`  ${value ? '✅' : '❌'} ${key}`);
    });
    
    console.log('\n🧩 Component Compliance:');
    Object.entries(results.compliance.components).forEach(([key, value]) => {
      console.log(`  ${value ? '✅' : '❌'} ${key}`);
    });
  }

  console.log('\n📸 Generated Screenshots:');
  results.screenshots.forEach(screenshot => {
    console.log(`  ${screenshot.viewport}: ${screenshot.file}`);
  });

  await browser.close();
  
  console.log('\n🎉 Visual design validation completed!');
  return results;
}

// Run validation
validateVisualDesign().catch(console.error);

export { validateVisualDesign };