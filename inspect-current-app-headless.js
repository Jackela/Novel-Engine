/**
 * Current Application Inspector (Headless)
 * =======================================
 * 
 * Headless inspection of the current frontend application
 */

const { chromium } = require('playwright');

async function inspectCurrentApplication() {
  console.log('🔍 Inspecting Current Frontend Application...');
  
  const browser = await chromium.launch({ headless: true });
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
      
      return {
        childCount: children.length,
        children: children.map((child, index) => ({
          index: index,
          tagName: child.tagName,
          className: child.className,
          id: child.id,
          textContent: child.textContent?.substring(0, 200),
          hasChildren: child.children.length > 0,
          childCount: child.children.length
        }))
      };
    });
    
    console.log(`\n📋 Body has ${bodyContent.childCount} direct children:`);
    bodyContent.children.forEach((element) => {
      console.log(`  ${element.index + 1}. <${element.tagName.toLowerCase()}>${element.id ? ` id="${element.id}"` : ''}${element.className ? ` class="${element.className}"` : ''}`);
      console.log(`     Children: ${element.childCount}`);
      if (element.textContent && element.textContent.trim()) {
        console.log(`     Text: "${element.textContent.substring(0, 100)}..."`);
      }
    });
    
    // Look for React root and components
    const reactInfo = await page.evaluate(() => {
      const root = document.getElementById('root');
      if (root) {
        return {
          present: true,
          innerHTML: root.innerHTML.substring(0, 1000),
          childCount: root.children.length,
          firstChildTag: root.children[0]?.tagName,
          firstChildClass: root.children[0]?.className,
          hasReactProps: Object.keys(root).some(key => key.startsWith('__react'))
        };
      }
      return { present: false };
    });
    
    console.log('\n⚛️  React Application Info:');
    if (reactInfo.present) {
      console.log(`  ✅ React root found with ${reactInfo.childCount} children`);
      console.log(`  First child: <${reactInfo.firstChildTag?.toLowerCase()}> class="${reactInfo.firstChildClass}"`);
      console.log(`  React props detected: ${reactInfo.hasReactProps ? 'Yes' : 'No'}`);
      console.log(`  Content preview: ${reactInfo.innerHTML.substring(0, 300)}...`);
    } else {
      console.log('  ❌ No React root element found');
    }
    
    // Check for specific content
    const contentAnalysis = await page.evaluate(() => {
      const text = document.body.innerText;
      const lowerText = text.toLowerCase();
      
      return {
        hasNovelEngine: lowerText.includes('novel engine'),
        hasDashboard: lowerText.includes('dashboard'),
        hasEmergent: lowerText.includes('emergent'),
        hasNarrative: lowerText.includes('narrative'),
        hasError: lowerText.includes('error') || lowerText.includes('404') || lowerText.includes('not found'),
        hasLoading: lowerText.includes('loading'),
        hasWelcome: lowerText.includes('welcome'),
        hasSetup: lowerText.includes('setup') || lowerText.includes('getting started'),
        textLength: text.length,
        fullText: text.substring(0, 2000)
      };
    });
    
    console.log('\n📝 Content Analysis:');
    console.log(`  Text length: ${contentAnalysis.textLength} characters`);
    console.log(`  Contains "Novel Engine": ${contentAnalysis.hasNovelEngine ? '✅' : '❌'}`);
    console.log(`  Contains "Dashboard": ${contentAnalysis.hasDashboard ? '✅' : '❌'}`);
    console.log(`  Contains "Emergent": ${contentAnalysis.hasEmergent ? '✅' : '❌'}`);
    console.log(`  Contains "Narrative": ${contentAnalysis.hasNarrative ? '✅' : '❌'}`);
    console.log(`  Contains Error: ${contentAnalysis.hasError ? '⚠️  YES' : '❌'}`);
    console.log(`  Contains Loading: ${contentAnalysis.hasLoading ? '⏳ YES' : '❌'}`);
    console.log(`  Contains Welcome/Setup: ${(contentAnalysis.hasWelcome || contentAnalysis.hasSetup) ? '🏠 YES' : '❌'}`);
    
    console.log('\n📄 Full Visible Text Content:');
    console.log(`"${contentAnalysis.fullText}"`);
    
    // Look for any data-testid attributes
    const testIds = await page.evaluate(() => {
      const elements = document.querySelectorAll('[data-testid]');
      return Array.from(elements).map(el => ({
        testId: el.getAttribute('data-testid'),
        tagName: el.tagName,
        visible: el.offsetParent !== null,
        text: el.textContent?.substring(0, 100)
      }));
    });
    
    console.log('\n🏷️  Data-TestId Elements:');
    if (testIds.length > 0) {
      testIds.forEach(element => {
        console.log(`  - [data-testid="${element.testId}"] (${element.tagName.toLowerCase()}) - ${element.visible ? 'VISIBLE' : 'HIDDEN'}`);
        if (element.text?.trim()) {
          console.log(`    Text: "${element.text}"`);
        }
      });
    } else {
      console.log('  ❌ No data-testid elements found');
    }
    
    // Look for common UI elements
    const uiElements = await page.evaluate(() => {
      return {
        buttons: document.querySelectorAll('button').length,
        inputs: document.querySelectorAll('input').length,
        links: document.querySelectorAll('a').length,
        headings: document.querySelectorAll('h1, h2, h3, h4, h5, h6').length,
        divs: document.querySelectorAll('div').length,
        images: document.querySelectorAll('img').length,
        canvases: document.querySelectorAll('canvas').length,
        svgs: document.querySelectorAll('svg').length
      };
    });
    
    console.log('\n🧩 UI Element Count:');
    Object.entries(uiElements).forEach(([element, count]) => {
      if (count > 0) {
        console.log(`  ${element}: ${count}`);
      }
    });
    
    // Take screenshot
    await page.screenshot({ 
      path: './final-validation-screenshots/current-app-inspection.png',
      fullPage: true
    });
    
    console.log('\n📸 Screenshot captured: ./final-validation-screenshots/current-app-inspection.png');
    
  } catch (error) {
    console.error('❌ Inspection failed:', error.message);
  } finally {
    await browser.close();
  }
}

// Run inspection
inspectCurrentApplication().then(() => {
  console.log('\n✅ Inspection completed');
}).catch(error => {
  console.error('❌ Inspection error:', error);
});