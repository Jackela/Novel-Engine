import { chromium } from 'playwright';

async function detailedDiagnostic() {
  console.log('🔍 Running detailed frontend diagnostic...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--no-sandbox', '--disable-web-security'],
    devtools: true
  });
  
  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();
    
    console.log('📊 Setting up detailed logging...');
    
    // Capture all console messages
    const consoleMessages = [];
    page.on('console', msg => {
      const message = `[${msg.type().toUpperCase()}] ${msg.text()}`;
      consoleMessages.push(message);
      console.log(`🔗 Console: ${message}`);
    });
    
    // Capture page errors
    const pageErrors = [];
    page.on('pageerror', error => {
      const errorMsg = `${error.name}: ${error.message}`;
      pageErrors.push(errorMsg);
      console.log(`🚨 Page Error: ${errorMsg}`);
      console.log(`   Stack: ${error.stack?.slice(0, 200)}...`);
    });
    
    // Capture network failures
    const networkErrors = [];
    page.on('requestfailed', request => {
      const failure = `${request.method()} ${request.url()} - ${request.failure()?.errorText}`;
      networkErrors.push(failure);
      console.log(`🌐 Network Failed: ${failure}`);
    });
    
    console.log('🌐 Navigating to frontend...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'domcontentloaded',
      timeout: 30000 
    });
    
    console.log('⏳ Waiting for React initialization...');
    await page.waitForTimeout(5000);
    
    // Check for process object
    console.log('\n🔍 Checking process object availability...');
    const processCheck = await page.evaluate(() => {
      return {
        processExists: typeof process !== 'undefined',
        processEnvExists: typeof process?.env !== 'undefined',
        processEnvNodeEnv: process?.env?.NODE_ENV,
        globalExists: typeof global !== 'undefined',
        windowExists: typeof window !== 'undefined'
      };
    });
    
    console.log('  Process check results:', processCheck);
    
    // Check React mounting
    console.log('\n🔍 Checking React mounting...');
    const reactCheck = await page.evaluate(() => {
      const root = document.getElementById('root');
      return {
        rootExists: !!root,
        rootHasChildren: root ? root.children.length > 0 : false,
        rootInnerHTML: root ? root.innerHTML.slice(0, 200) : 'No root element',
        reactDevToolsExists: !!window.__REACT_DEVTOOLS_GLOBAL_HOOK__,
        bodyChildren: document.body.children.length,
        headChildren: document.head.children.length,
        scriptsLoaded: Array.from(document.scripts).map(s => s.src || s.textContent?.slice(0, 50))
      };
    });
    
    console.log('  React check results:', reactCheck);
    
    // Check for any missing dependencies
    console.log('\n🔍 Checking for missing global dependencies...');
    const globalCheck = await page.evaluate(() => {
      const globals = ['React', 'ReactDOM', 'Buffer'];
      const results = {};
      globals.forEach(globalName => {
        results[globalName] = typeof window[globalName] !== 'undefined';
      });
      return results;
    });
    
    console.log('  Global dependencies:', globalCheck);
    
    // Try to trigger React manually if it's loaded but not mounted
    console.log('\n🔧 Attempting manual React initialization...');
    const manualInit = await page.evaluate(() => {
      try {
        // Check if React and ReactDOM are available
        if (typeof React !== 'undefined' && typeof ReactDOM !== 'undefined') {
          console.log('React and ReactDOM are available');
          return { reactAvailable: true, reactDOMAvailable: true };
        } else {
          console.log('React or ReactDOM not available globally');
          return { reactAvailable: false, reactDOMAvailable: false };
        }
      } catch (error) {
        return { error: error.message };
      }
    });
    
    console.log('  Manual init result:', manualInit);
    
    // Take screenshot
    await page.screenshot({ 
      path: 'detailed-diagnostic.png', 
      fullPage: true 
    });
    
    console.log('\n📋 Diagnostic Summary:');
    console.log('  Console messages:', consoleMessages.length);
    console.log('  Page errors:', pageErrors.length);
    console.log('  Network errors:', networkErrors.length);
    console.log('  Process available:', processCheck.processExists);
    console.log('  React mounted:', reactCheck.rootHasChildren);
    
    return {
      success: reactCheck.rootHasChildren,
      processCheck,
      reactCheck,
      globalCheck,
      consoleMessages,
      pageErrors,
      networkErrors
    };
    
  } catch (error) {
    console.log('❌ Diagnostic failed:', error.message);
    return { success: false, error: error.message };
  } finally {
    // Keep browser open for manual inspection
    console.log('\n🔍 Browser left open for manual inspection...');
    setTimeout(() => {
      browser.close();
    }, 30000); // Close after 30 seconds
  }
}

// Run the diagnostic
detailedDiagnostic().then(result => {
  console.log('\n📊 Final Diagnostic Result:', {
    success: result.success,
    processAvailable: result.processCheck?.processExists,
    reactMounted: result.reactCheck?.rootHasChildren,
    errorCount: result.pageErrors?.length || 0
  });
}).catch(err => {
  console.error('Fatal diagnostic error:', err);
});