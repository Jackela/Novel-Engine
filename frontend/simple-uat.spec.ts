import { test, expect } from '@playwright/test';

test('Simple Dashboard UAT with Real API', async ({ page }) => {
  console.log('🎯 Starting Simple UAT with Real API');
  
  // Navigate to dashboard
  await page.goto('http://localhost:3001');
  
  // Wait for page to load
  await page.waitForTimeout(2000);
  
  // Take screenshot for evidence
  await page.screenshot({ path: 'uat-evidence/dashboard-loaded.png', fullPage: true });
  
  // Check if basic elements are present
  const titleElement = await page.textContent('title');
  console.log('Page title:', titleElement);
  
  // Look for any interactive elements
  const buttons = await page.locator('button').count();
  console.log('Number of buttons found:', buttons);
  
  // Look for any form elements  
  const inputs = await page.locator('input').count();
  console.log('Number of inputs found:', inputs);
  
  // Check for API calls being made
  const responses = [];
  page.on('response', response => {
    if (response.url().includes('localhost:8000')) {
      responses.push({
        url: response.url(),
        status: response.status(),
        statusText: response.statusText()
      });
    }
  });
  
  // Wait for any API calls to complete
  await page.waitForTimeout(3000);
  
  console.log('API responses captured:', responses);
  
  // Final screenshot
  await page.screenshot({ path: 'uat-evidence/dashboard-final.png', fullPage: true });
  
  // Basic assertion that page loaded
  expect(await page.title()).toBeTruthy();
});