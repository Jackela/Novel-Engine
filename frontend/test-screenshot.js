import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(3000); // Wait for backend connection
  await page.screenshot({ path: 'frontend-fixed-screenshot.png' });
  await browser.close();
})();