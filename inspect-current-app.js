/**
 * Current Application Inspector
 * ===========================
 * 
 * Inspect what's currently being served by the frontend
 * to understand the gap between expected dashboard and actual state
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function inspectCurrentApplication() {
  console.log('🔍 Inspecting Current Frontend Application...');
  
  const browser = await chromium.launch({ headless: false }); // Show browser for inspection
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  
  const page = await context.newPage();
  
  try {
    // Load the application
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    console.log('✅ Application loaded successfully');
    
    // Get the page title
    const title = await page.title();
    console.log(`📄 Page title: ${title}`);
    
    // Get the main content structure
    const bodyContent = await page.evaluate(() => {
      const body = document.body;
      const children = Array.from(body.children);
      
      return children.map(child => ({
        tagName: child.tagName,
        className: child.className,
        id: child.id,
        textContent: child.textContent?.substring(0, 100) + '...',
        hasChildren: child.children.length > 0,
        childCount: child.children.length
      }));
    });
    
    console.log('\n📋 Body Content Structure:');
    bodyContent.forEach((element, index) => {
      console.log(`  ${index + 1}. <${element.tagName.toLowerCase()}> 
      Class: "${element.className}"
      ID: "${element.id}"
      Children: ${element.childCount}
      Text: ${element.textContent}`);
    });
    
    // Look for React root and components
    const reactInfo = await page.evaluate(() => {
      const root = document.getElementById('root');
      if (root) {
        return {
          present: true,
          innerHTML: root.innerHTML.substring(0, 500),
          childCount: root.children.length,
          firstChildTag: root.children[0]?.tagName,
          reactProps: Object.keys(root).filter(key => key.startsWith('__react'))
        };
      }
      return { present: false };
    });
    
    console.log('\n⚛️  React Application Info:');
    if (reactInfo.present) {
      console.log(`  Root element found with ${reactInfo.childCount} children`);
      console.log(`  First child: <${reactInfo.firstChildTag?.toLowerCase()}>`);
      console.log(`  React props detected: ${reactInfo.reactProps.length > 0 ? 'Yes' : 'No'}`);
      console.log(`  Content preview: ${reactInfo.innerHTML.substring(0, 200)}...`);
    } else {
      console.log('  ❌ No React root element found');
    }
    
    // Check for specific content that might indicate what's being served
    const contentAnalysis = await page.evaluate(() => {
      const text = document.body.innerText.toLowerCase();
      
      return {
        hasNovelEngine: text.includes('novel engine'),
        hasDashboard: text.includes('dashboard'),
        hasEmergent: text.includes('emergent'),
        hasNarrative: text.includes('narrative'),
        hasError: text.includes('error') || text.includes('404'),
        hasLoading: text.includes('loading'),
        hasWelcome: text.includes('welcome'),
        hasSetup: text.includes('setup') || text.includes('getting started'),
        fullText: text.substring(0, 1000)
      };
    });
    
    console.log('\n📝 Content Analysis:');
    console.log(`  Contains "Novel Engine": ${contentAnalysis.hasNovelEngine ? '✅' : '❌'}`);
    console.log(`  Contains "Dashboard": ${contentAnalysis.hasDashboard ? '✅' : '❌'}`);
    console.log(`  Contains "Emergent": ${contentAnalysis.hasEmergent ? '✅' : '❌'}`);
    console.log(`  Contains "Narrative": ${contentAnalysis.hasNarrative ? '✅' : '❌'}`);
    console.log(`  Contains Error: ${contentAnalysis.hasError ? '⚠️  Yes' : '❌'}`);
    console.log(`  Contains Loading: ${contentAnalysis.hasLoading ? '⏳ Yes' : '❌'}`);
    console.log(`  Contains Welcome/Setup: ${contentAnalysis.hasWelcome || contentAnalysis.hasSetup ? '🏠 Yes' : '❌'}`);
    
    console.log('\n📄 Full Text Content (first 1000 chars):');
    console.log(`"${contentAnalysis.fullText}"`);
    
    // Look for any data-testid attributes
    const testIds = await page.evaluate(() => {
      const elements = document.querySelectorAll('[data-testid]');
      return Array.from(elements).map(el => ({
        testId: el.getAttribute('data-testid'),
        tagName: el.tagName,
        visible: el.offsetParent !== null,
        text: el.textContent?.substring(0, 50)
      }));
    });
    
    console.log('\n🏷️  Data-TestId Elements Found:');
    if (testIds.length > 0) {
      testIds.forEach(element => {
        console.log(`  - ${element.testId} (${element.tagName.toLowerCase()}) - ${element.visible ? 'Visible' : 'Hidden'}`);
        if (element.text) console.log(`    Text: "${element.text}..."`);
      });
    } else {
      console.log('  ❌ No data-testid elements found');
    }
    
    // Take a full screenshot to see what's actually displayed
    await page.screenshot({ 
      path: './final-validation-screenshots/current-app-inspection.png',
      fullPage: true
    });
    
    console.log('\n📸 Screenshot saved: ./final-validation-screenshots/current-app-inspection.png');
    
    // Keep browser open for manual inspection
    console.log('\n👀 Browser left open for manual inspection. Press Enter to close...');
    
    // Wait for user input in a non-blocking way
    return new Promise((resolve) => {
      const readline = require('readline');
      const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
      });
      
      rl.question('Press Enter to close browser and continue...', () => {
        rl.close();
        resolve();
      });
    });
    
  } catch (error) {
    console.error('❌ Inspection failed:', error.message);
  } finally {
    await browser.close();
  }
}

// Run inspection
inspectCurrentApplication();