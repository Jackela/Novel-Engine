import { chromium } from 'playwright';

async function runDiagnosticTest() {
  console.log('🔍 Starting Diagnostic Test for Frontend Application');
  
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Capture console messages
  const consoleMessages = [];
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    consoleMessages.push(`[${type.toUpperCase()}] ${text}`);
    console.log(`[CONSOLE ${type.toUpperCase()}] ${text}`);
  });
  
  // Capture page errors
  const pageErrors = [];
  page.on('pageerror', error => {
    pageErrors.push(error.message);
    console.error(`[PAGE ERROR] ${error.message}`);
  });
  
  // Capture network failures
  const networkFailures = [];
  page.on('response', response => {
    if (response.status() >= 400) {
      networkFailures.push(`${response.status()} ${response.url()}`);
      console.error(`[NETWORK ERROR] ${response.status()} ${response.url()}`);
    }
  });
  
  try {
    console.log('🌐 Testing different routes...');
    
    // Test root route
    console.log('📍 Testing root route (/)');
    await page.goto('http://localhost:3003/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'diagnostic-root.png', fullPage: true });
    
    // Test dashboard route
    console.log('📍 Testing dashboard route (/dashboard)');
    await page.goto('http://localhost:3003/dashboard', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'diagnostic-dashboard.png', fullPage: true });
    
    // Check DOM content
    const bodyContent = await page.locator('body').innerHTML();
    const hasContent = bodyContent.length > 100;
    
    console.log(`📄 Body content length: ${bodyContent.length} characters`);
    console.log(`📄 Has substantial content: ${hasContent}`);
    
    if (bodyContent.length < 500) {
      console.log('📄 Full body content:', bodyContent);
    }
    
    // Check for React app mounting
    const reactRoot = await page.locator('#root').count();
    console.log(`⚛️  React root elements found: ${reactRoot}`);
    
    // Try to find any visible elements
    const allElements = await page.locator('*').count();
    const visibleElements = await page.locator('*:visible').count();
    console.log(`🔍 Total elements: ${allElements}, Visible: ${visibleElements}`);
    
    // Check if we can find Material-UI components
    const muiElements = await page.locator('[class*="Mui"], [class*="mui"]').count();
    console.log(`🎨 Material-UI elements found: ${muiElements}`);
    
    // Check for error boundaries or error messages
    const errorElements = await page.locator('text=error, text=Error, [class*="error"], [class*="Error"]').count();
    console.log(`❌ Error elements found: ${errorElements}`);
    
  } catch (error) {
    console.error('🚨 Diagnostic Test Error:', error);
  }
  
  // Summary
  console.log('\n📊 Diagnostic Summary:');
  console.log(`   Console messages: ${consoleMessages.length}`);
  console.log(`   Page errors: ${pageErrors.length}`);
  console.log(`   Network failures: ${networkFailures.length}`);
  
  if (consoleMessages.length > 0) {
    console.log('\n📝 Console Messages:');
    consoleMessages.forEach(msg => console.log(`   ${msg}`));
  }
  
  if (pageErrors.length > 0) {
    console.log('\n🚨 Page Errors:');
    pageErrors.forEach(error => console.log(`   ${error}`));
  }
  
  if (networkFailures.length > 0) {
    console.log('\n🌐 Network Failures:');
    networkFailures.forEach(failure => console.log(`   ${failure}`));
  }
  
  await browser.close();
}

runDiagnosticTest().catch(console.error);