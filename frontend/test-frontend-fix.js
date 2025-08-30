import { chromium } from 'playwright';

async function testFrontendFix() {
  console.log('🧪 Testing frontend fix for process.env issue...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--no-sandbox', '--disable-web-security']
  });
  
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // Listen for all console messages
    page.on('console', msg => {
      console.log(`📝 Console ${msg.type()}:`, msg.text());
    });
    
    // Listen for page errors
    page.on('pageerror', error => {
      console.log('🚨 Page error:', error.message);
    });
    
    // Navigate to frontend
    console.log('🌐 Loading frontend at http://localhost:3002...');
    await page.goto('http://localhost:3002', { 
      waitUntil: 'domcontentloaded',
      timeout: 30000 
    });
    
    // Wait a bit for React to render
    await page.waitForTimeout(3000);
    
    // Check if page loaded
    const title = await page.title();
    console.log('📖 Page title:', title);
    
    // Get the actual HTML content to see what's rendering
    const bodyContent = await page.evaluate(() => document.body.innerHTML);
    console.log('📄 Body content preview:', bodyContent.slice(0, 500) + (bodyContent.length > 500 ? '...' : ''));
    
    // Check if React root exists
    const rootDiv = await page.$('#root');
    console.log('🌳 Root div exists:', rootDiv !== null);
    
    // Look for any elements
    const anyElements = [
      '#root > *', // Any child of root
      'div', // Any div
      'button', // Any button
      'h1, h2, h3, h4, h5, h6', // Any headers
      '[class*="MuiContainer"]', // Any MUI container class
      '[class*="MuiCard"]', // Any MUI card class
      '.MuiContainer-root',
      '[data-testid="dashboard-layout"]'
    ];
    
    let foundElements = [];
    for (const selector of anyElements) {
      const element = await page.$(selector);
      if (element) {
        foundElements.push(selector);
      }
    }
    
    console.log('✅ Found elements:', foundElements);
    
    // Take screenshot
    await page.screenshot({ 
      path: 'frontend-fix-test.png', 
      fullPage: true 
    });
    console.log('📸 Screenshot saved as frontend-fix-test.png');
    
    // Check for any runtime errors
    const hasErrors = await page.evaluate(() => {
      return window.__hasRuntimeError || false;
    });
    
    if (foundElements.length > 0) {
      console.log('🎉 Frontend appears to be loading successfully!');
      return true;
    } else {
      console.log('⚠️ Frontend loaded but no expected elements found');
      return false;
    }
    
  } catch (error) {
    console.log('❌ Test failed:', error.message);
    return false;
  } finally {
    await browser.close();
  }
}

// Run the test
testFrontendFix().then(success => {
  console.log(success ? '\n✅ Test completed successfully' : '\n❌ Test failed');
  process.exit(success ? 0 : 1);
}).catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});