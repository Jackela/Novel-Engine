import { chromium } from 'playwright';

async function quickTest() {
  console.log('🚀 Quick polyfill test...');
  
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Log all console messages and errors
  page.on('console', msg => console.log(`📝 ${msg.type()}: ${msg.text()}`));
  page.on('pageerror', error => console.log(`🚨 Error: ${error.message}`));
  
  await page.goto('http://localhost:3000');
  await page.waitForTimeout(3000);
  
  // Check if process is now defined
  const processTest = await page.evaluate(() => {
    return {
      processExists: typeof process !== 'undefined',
      processEnv: process?.env || 'undefined',
      hasNodeEnv: !!process?.env?.NODE_ENV
    };
  });
  
  console.log('🔍 Process test:', processTest);
  
  // Check React mounting
  const reactTest = await page.evaluate(() => {
    const root = document.getElementById('root');
    return {
      rootChildren: root ? root.children.length : 0,
      rootContent: root ? root.innerHTML.length : 0
    };
  });
  
  console.log('⚛️ React test:', reactTest);
  
  await browser.close();
  
  return {
    processWorks: processTest.processExists && processTest.hasNodeEnv,
    reactMounted: reactTest.rootChildren > 0
  };
}

quickTest().then(result => {
  console.log('\n✅ Test result:', result);
  if (result.processWorks && result.reactMounted) {
    console.log('🎉 SUCCESS: Frontend is working!');
  } else if (result.processWorks && !result.reactMounted) {
    console.log('⚠️ Process fixed but React not mounting');
  } else {
    console.log('❌ Process polyfill still not working');
  }
});