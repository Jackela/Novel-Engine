/**
 * Frontend Debug Script
 * ====================
 * 
 * Debug why the React application is not rendering
 */

const { chromium } = require('playwright');

async function debugFrontendIssues() {
  console.log('🐛 Debugging Frontend Issues...');
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  
  const page = await context.newPage();
  
  // Capture console messages
  const consoleMessages = [];
  page.on('console', msg => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text(),
      location: msg.location()
    });
  });
  
  // Capture page errors
  const pageErrors = [];
  page.on('pageerror', error => {
    pageErrors.push({
      message: error.message,
      stack: error.stack
    });
  });
  
  // Capture failed network requests
  const failedRequests = [];
  page.on('response', response => {
    if (!response.ok()) {
      failedRequests.push({
        url: response.url(),
        status: response.status(),
        statusText: response.statusText()
      });
    }
  });
  
  try {
    console.log('📡 Loading application and capturing errors...');
    
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Wait a moment for any async errors
    await page.waitForTimeout(5000);
    
    console.log('\n📋 Debug Results:');
    console.log('=================');
    
    // Console Messages
    console.log(`\n💬 Console Messages (${consoleMessages.length}):`);
    if (consoleMessages.length > 0) {
      consoleMessages.forEach((msg, index) => {
        console.log(`  ${index + 1}. [${msg.type.toUpperCase()}] ${msg.text}`);
        if (msg.location.url && msg.location.lineNumber) {
          console.log(`     Location: ${msg.location.url}:${msg.location.lineNumber}`);
        }
      });
    } else {
      console.log('  ✅ No console messages');
    }
    
    // Page Errors
    console.log(`\n❌ JavaScript Errors (${pageErrors.length}):`);
    if (pageErrors.length > 0) {
      pageErrors.forEach((error, index) => {
        console.log(`  ${index + 1}. ${error.message}`);
        if (error.stack) {
          console.log(`     Stack: ${error.stack.split('\\n')[0]}`);
        }
      });
    } else {
      console.log('  ✅ No JavaScript errors');
    }
    
    // Failed Requests
    console.log(`\n🌐 Failed Network Requests (${failedRequests.length}):`);
    if (failedRequests.length > 0) {
      failedRequests.forEach((req, index) => {
        console.log(`  ${index + 1}. ${req.status} ${req.statusText}: ${req.url}`);
      });
    } else {
      console.log('  ✅ No failed network requests');
    }
    
    // Check if React is loaded
    const reactStatus = await page.evaluate(() => {
      return {
        reactLoaded: typeof window.React !== 'undefined',
        reactDOMLoaded: typeof window.ReactDOM !== 'undefined',
        viteClientLoaded: typeof window.__vite_plugin_react !== 'undefined',
        hasReactDevTools: typeof window.__REACT_DEVTOOLS_GLOBAL_HOOK__ !== 'undefined',
        rootElement: !!document.getElementById('root'),
        rootHasReactFiber: !!document.getElementById('root')?._reactInternalFiber,
        windowKeys: Object.keys(window).filter(k => k.includes('React') || k.includes('__')).slice(0, 10)
      };
    });
    
    console.log('\\n⚛️  React Status:');
    console.log(`  React loaded: ${reactStatus.reactLoaded ? '✅' : '❌'}`);
    console.log(`  ReactDOM loaded: ${reactStatus.reactDOMLoaded ? '✅' : '❌'}`);
    console.log(`  Vite client loaded: ${reactStatus.viteClientLoaded ? '✅' : '❌'}`);
    console.log(`  React DevTools: ${reactStatus.hasReactDevTools ? '✅' : '❌'}`);
    console.log(`  Root element exists: ${reactStatus.rootElement ? '✅' : '❌'}`);
    console.log(`  Root has React fiber: ${reactStatus.rootHasReactFiber ? '✅' : '❌'}`);
    console.log(`  Window React keys: ${reactStatus.windowKeys.join(', ')}`);
    
    // Check loaded scripts
    const scripts = await page.evaluate(() => {
      return Array.from(document.scripts).map(script => ({
        src: script.src,
        type: script.type,
        loaded: !script.src || script.readyState === 'complete' || script.readyState === 'loaded',
        hasError: script.onerror !== null
      }));
    });
    
    console.log(`\\n📜 Loaded Scripts (${scripts.length}):`);
    scripts.forEach((script, index) => {
      if (script.src) {
        const filename = script.src.split('/').pop();
        console.log(`  ${index + 1}. ${filename} - ${script.loaded ? '✅ Loaded' : '❌ Not Loaded'}`);
      }
    });
    
    // Check if main.tsx exists and was loaded
    const mainAppStatus = await page.evaluate(() => {
      const scripts = Array.from(document.scripts);
      const viteScript = scripts.find(s => s.src.includes('/@vite/client'));
      const mainScript = scripts.find(s => s.src.includes('/src/main'));
      
      return {
        viteClientScript: !!viteScript,
        mainAppScript: !!mainScript,
        totalScripts: scripts.length,
        scriptsSrc: scripts.map(s => s.src).filter(Boolean).map(src => src.split('/').pop())
      };
    });
    
    console.log('\\n🚀 Application Bootstrap:');
    console.log(`  Vite client script: ${mainAppStatus.viteClientScript ? '✅' : '❌'}`);
    console.log(`  Main app script: ${mainAppStatus.mainAppScript ? '✅' : '❌'}`);
    console.log(`  Total scripts: ${mainAppStatus.totalScripts}`);
    console.log(`  Script files: ${mainAppStatus.scriptsSrc.join(', ')}`);
    
  } catch (error) {
    console.error('❌ Debug failed:', error.message);
  } finally {
    await browser.close();
  }
}

// Run debug
debugFrontendIssues().then(() => {
  console.log('\\n✅ Debug completed');
}).catch(error => {
  console.error('❌ Debug error:', error);
});