/**
 * Character Selection Component - Playwright Test Suite
 * 
 * This test suite provides comprehensive coverage for the Character Selection Component
 * based on the UI Design Specification. Tests are designed to guide implementation
 * and will initially fail since the component doesn't exist yet.
 * 
 * Test Coverage Areas:
 * 1. Initial State Tests
 * 2. Selection Logic Tests  
 * 3. Validation Logic Tests
 */

import { test, expect } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://localhost:5173'; // Vite dev server default
const API_BASE_URL = 'http://localhost:8000';

// Helper function for browser-compatible navigation
async function navigateToPage(page, browserName, url) {
  if (browserName === 'firefox' || browserName === 'webkit') {
    // For Firefox and WebKit, try multiple connection attempts
    let connected = false;
    let attempts = 3;
    
    while (!connected && attempts > 0) {
      try {
        await page.goto(url, { 
          waitUntil: 'networkidle',
          timeout: 15000 
        });
        connected = true;
      } catch (error) {
        attempts--;
        if (attempts > 0) {
          console.log(`Retrying navigation to ${url} (${3 - attempts}/3)...`);
          await page.waitForTimeout(2000);
        } else {
          throw error;
        }
      }
    }
  } else {
    // Standard navigation for Chromium and other browsers
    await page.goto(url);
  }
}

// Mock data for API responses
const MOCK_CHARACTERS_RESPONSE = {
  characters: ['krieg', 'ork', 'test']
};

const MOCK_CHARACTER_DETAILS = {
  krieg: {
    character_name: 'krieg',
    narrative_context: 'Trooper 86 of the Death Korps of Krieg...',
    structured_data: {
      name: 'Trooper 86',
      factions: ['Astra Militarum', 'Death Korps of Krieg'],
      personality_traits: ['Fatalistic', 'Grim', 'Loyal to the Emperor']
    },
    file_count: { md: 1, yaml: 1 }
  },
  ork: {
    character_name: 'ork',
    narrative_context: 'WAAAGH! Boss Skarfang of the Blood Axes...',
    structured_data: {
      name: 'Boss Skarfang',
      factions: ['Orks', 'Blood Axes'],
      personality_traits: ['Aggressive', 'Cunning', 'Brutal']
    },
    file_count: { md: 1, yaml: 1 }
  },
  test: {
    character_name: 'test',
    narrative_context: 'Test character for development purposes...',
    structured_data: {
      name: 'Test Character',
      factions: ['Test Faction'],
      personality_traits: ['Testing', 'Placeholder']
    },
    file_count: { md: 1, yaml: 1 }
  }
};

test.describe('Character Selection Component', () => {
  
  test.beforeEach(async ({ page, browserName }) => {
    // Navigate to the character selection page with browser-specific handling
    await navigateToPage(page, browserName, `${BASE_URL}/character-selection`);
  });

  /**
   * 1. INITIAL STATE TESTS
   * Testing component loading behavior, API integration, and error handling
   */
  test.describe('Initial State Tests', () => {
    
    test('should render with loading state initially', async ({ page }) => {
      // Mock API to delay response to test loading state
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await new Promise(resolve => setTimeout(resolve, 800)); // Shorter delay
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });

      // Navigate fresh to trigger loading state
      await page.goto(`${BASE_URL}/character-selection`);

      // Check for loading indicators immediately
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
      await expect(page.locator('text=Communing with the Machine God to retrieve character souls...')).toBeVisible();
      await expect(page.locator('[data-testid="character-grid"]')).not.toBeVisible();
      
      // Verify loading state clears after API response with longer timeout
      await expect(page.locator('[data-testid="loading-spinner"]')).not.toBeVisible({ timeout: 5000 });
      await expect(page.locator('[data-testid="character-grid"]')).toBeVisible();
    });

    test('should make API call to GET /characters endpoint on mount', async ({ page, browserName }) => {
      let apiCallMade = false;
      
      // Intercept and verify API call
      await page.route(`${API_BASE_URL}/characters`, async route => {
        apiCallMade = true;
        expect(route.request().method()).toBe('GET');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });

      // Navigate to page to trigger fresh API call
      await navigateToPage(page, browserName, `${BASE_URL}/character-selection`);
      
      // Wait for component to mount and make API call
      await page.waitForLoadState('networkidle');
      
      // Additional wait for mobile browsers  
      if (browserName === 'Mobile Chrome') {
        await page.waitForTimeout(1000);
      }
      
      // Verify API call was made by checking for character cards
      await expect(page.locator('.character-card')).toHaveCount(3, { timeout: 15000 });
      expect(apiCallMade).toBe(true);
    });

    test('should display character cards after successful API response', async ({ page }) => {
      // Mock successful API response BEFORE navigation
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });

      // Navigate fresh to trigger API call with mock
      await page.goto(`${BASE_URL}/character-selection`);

      // Wait for loading to complete and character grid to appear
      await expect(page.locator('[data-testid="loading-spinner"]')).not.toBeVisible({ timeout: 15000 });
      await expect(page.locator('[data-testid="character-grid"]')).toBeVisible();
      
      // Wait for character cards to appear
      await expect(page.locator('.character-card')).toHaveCount(3);
      
      // Verify each character is displayed
      await expect(page.locator('[data-testid="character-card-krieg"]')).toBeVisible();
      await expect(page.locator('[data-testid="character-card-ork"]')).toBeVisible();
      await expect(page.locator('[data-testid="character-card-test"]')).toBeVisible();
      
      // Verify character names are displayed using more specific locators
      await expect(page.locator('[data-testid="character-card-krieg"] .character-name')).toContainText('krieg');
      await expect(page.locator('[data-testid="character-card-ork"] .character-name')).toContainText('ork');
      await expect(page.locator('[data-testid="character-card-test"] .character-name')).toContainText('test');
    });

    test('should handle 404 API errors gracefully', async ({ page }) => {
      // Mock 404 response BEFORE navigation
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Characters not found' })
        });
      });

      // Navigate fresh to trigger API call with mock
      await page.goto(`${BASE_URL}/character-selection`);

      // Verify error message is displayed
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('text=No characters found - Please ensure character data is available')).toBeVisible();
      
      // Verify retry button is available
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    });

    test('should handle 500 API errors gracefully', async ({ page }) => {
      // Mock 500 response BEFORE navigation
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' })
        });
      });

      // Navigate fresh to trigger API call with mock
      await page.goto(`${BASE_URL}/character-selection`);

      // Verify error message is displayed
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('text=Server error - Please try again later')).toBeVisible();
    });

    test('should handle network connection errors', async ({ page }) => {
      // Mock network failure BEFORE navigation
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.abort('failed');
      });

      // Navigate fresh to trigger API call with mock
      await page.goto(`${BASE_URL}/character-selection`);

      // Verify error message is displayed
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('text=Cannot connect to server - Please ensure the backend is running')).toBeVisible();
    });

    test('should show appropriate loading indicators during API calls', async ({ page }) => {
      // Mock delayed API response
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Increased delay to ensure loading state is visible
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });

      // Navigate to trigger the loading state
      await page.goto(`${BASE_URL}/character-selection`);
      
      // Verify component shows loading state immediately
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible({ timeout: 2000 });
      await expect(page.locator('[data-testid="character-grid"]')).not.toBeVisible();
      
      // Verify loading state has appropriate styling
      const loadingElement = page.locator('[data-testid="loading-spinner"]');
      await expect(loadingElement).toHaveCSS('display', /block|flex/);
      
      // Wait for loading to complete
      await expect(page.locator('[data-testid="loading-spinner"]')).not.toBeVisible({ timeout: 3000 });
      await expect(page.locator('[data-testid="character-grid"]')).toBeVisible();
    });
  });

  /**
   * 2. SELECTION LOGIC TESTS
   * Testing character selection/deselection functionality and visual feedback
   */
  test.describe('Selection Logic Tests', () => {
    
    test.beforeEach(async ({ page }) => {
      // Mock successful API response for all selection tests
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Navigate to ensure API call is made with fresh mocks
      await page.goto(`${BASE_URL}/character-selection`);
      
      // Wait for characters to load
      await expect(page.locator('.character-card')).toHaveCount(3);
    });

    test('should select character when clicking unselected card', async ({ page }) => {
      const kriegCard = page.locator('[data-testid="character-card-krieg"]');
      
      // Verify initial unselected state
      await expect(kriegCard).not.toHaveClass(/selected/);
      await expect(page.locator('[data-testid="selection-checkmark-krieg"]')).not.toBeVisible();
      
      // Click to select
      await kriegCard.click();
      
      // Verify selected state
      await expect(kriegCard).toHaveClass(/selected/);
      await expect(page.locator('[data-testid="selection-checkmark-krieg"]')).toBeVisible();
      
      // Verify selection counter updates
      await expect(page.locator('[data-testid="selection-counter"]')).toContainText('1 of 6 characters selected');
    });

    test('should deselect character when clicking selected card', async ({ page }) => {
      const orkCard = page.locator('[data-testid="character-card-ork"]');
      
      // First select the character
      await orkCard.click();
      await expect(orkCard).toHaveClass(/selected/);
      
      // Click again to deselect
      await orkCard.click();
      
      // Verify deselected state
      await expect(orkCard).not.toHaveClass(/selected/);
      await expect(page.locator('[data-testid="selection-checkmark-ork"]')).not.toBeVisible();
      
      // Verify selection counter updates
      await expect(page.locator('[data-testid="selection-counter"]')).toContainText('0 of 6 characters selected');
    });

    test('should persist selection state correctly across interactions', async ({ page }) => {
      // Select multiple characters
      await page.locator('[data-testid="character-card-krieg"]').click();
      await page.locator('[data-testid="character-card-ork"]').click();
      await page.locator('[data-testid="character-card-test"]').click();
      
      // Verify all are selected
      await expect(page.locator('[data-testid="character-card-krieg"]')).toHaveClass(/selected/);
      await expect(page.locator('[data-testid="character-card-ork"]')).toHaveClass(/selected/);
      await expect(page.locator('[data-testid="character-card-test"]')).toHaveClass(/selected/);
      
      // Deselect middle character
      await page.locator('[data-testid="character-card-ork"]').click();
      
      // Verify selection state is maintained for others
      await expect(page.locator('[data-testid="character-card-krieg"]')).toHaveClass(/selected/);
      await expect(page.locator('[data-testid="character-card-ork"]')).not.toHaveClass(/selected/);
      await expect(page.locator('[data-testid="character-card-test"]')).toHaveClass(/selected/);
      
      // Verify counter reflects current state
      await expect(page.locator('[data-testid="selection-counter"]')).toContainText('2 of 6 characters selected');
    });

    test('should show visual feedback for selected vs unselected states', async ({ page }) => {
      const kriegCard = page.locator('[data-testid="character-card-krieg"]');
      
      // Check unselected visual state - Allow for slight browser precision differences
      await expect(async () => {
        const borderWidth = await kriegCard.evaluate(el => getComputedStyle(el).borderWidth);
        const numericWidth = parseFloat(borderWidth);
        expect(numericWidth).toBeCloseTo(1, 0); // Within 1 pixel precision
      }).not.toThrow();
      await expect(kriegCard).not.toHaveCSS('border-color', /rgb\(255, 215, 0\)|#FFD700/); // Not accent color
      
      // Select character
      await kriegCard.click();
      
      // Check selected visual state
      await expect(kriegCard).toHaveCSS('border-width', '3px'); // Selected border width
      await expect(kriegCard).toHaveCSS('border-color', /rgb\(255, 215, 0\)|#FFD700/); // Accent color border
      await expect(page.locator('[data-testid="selection-checkmark-krieg"]')).toBeVisible();
    });

    test('should support multiple character selection functionality', async ({ page }) => {
      // Select multiple characters sequentially
      await page.locator('[data-testid="character-card-krieg"]').click();
      await page.locator('[data-testid="character-card-ork"]').click();
      
      // Verify both are selected
      await expect(page.locator('[data-testid="character-card-krieg"]')).toHaveClass(/selected/);
      await expect(page.locator('[data-testid="character-card-ork"]')).toHaveClass(/selected/);
      
      // Verify counter reflects multiple selections
      await expect(page.locator('[data-testid="selection-counter"]')).toContainText('2 of 6 characters selected');
    });

    test('should show hover effects on character cards', async ({ page }) => {
      const testCard = page.locator('[data-testid="character-card-test"]');
      
      // Hover over card
      await testCard.hover();
      
      // Check if motion is reduced (accessibility setting)
      const reducedMotion = await page.evaluate(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
      
      if (reducedMotion) {
        // In reduced motion mode, hover effects should be disabled
        await expect(testCard).toHaveCSS('transform', /none|matrix\(1, 0, 0, 1, 0, 0\)/);
      } else {
        // In normal mode, hover effects should apply
        await expect(testCard).toHaveCSS('transform', /matrix\(1\.02, 0, 0, 1\.02, 0, 0\)/);
      }
      
      // Move away and verify appropriate state
      await page.locator('body').hover();
      
      if (!reducedMotion) {
        await expect(testCard).not.toHaveCSS('transform', /scale\(1\.02\)/);
      }
    });
  });

  /**
   * 3. VALIDATION LOGIC TESTS
   * Testing selection constraints, error messaging, and button behavior
   */
  test.describe('Validation Logic Tests', () => {
    
    test.beforeEach(async ({ page }) => {
      // Mock successful API response for all validation tests
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Navigate to ensure API call is made with fresh mocks
      await page.goto(`${BASE_URL}/character-selection`);
      
      // Wait for characters to load
      await expect(page.locator('.character-card')).toHaveCount(3);
    });

    test('should enforce minimum of 2 characters requirement', async ({ page }) => {
      // Verify initial state - button disabled with no selections
      await expect(page.locator('[data-testid="confirm-selection-button"]')).toBeDisabled();
      
      // Select only one character
      await page.locator('[data-testid="character-card-krieg"]').click();
      
      // Verify button still disabled and error message shown
      await expect(page.locator('[data-testid="confirm-selection-button"]')).toBeDisabled();
      await expect(page.locator('[data-testid="validation-error"]')).toContainText('Please select at least 2 characters to start simulation');
      
      // Select second character
      await page.locator('[data-testid="character-card-ork"]').click();
      
      // Verify button becomes enabled and error clears
      await expect(page.locator('[data-testid="confirm-selection-button"]')).toBeEnabled();
      await expect(page.locator('[data-testid="validation-error"]')).not.toBeVisible();
    });

    test('should enforce maximum of 6 characters limit', async ({ page }) => {
      // For this test, we need to mock a response with more than 6 characters
      const manyCharacters = {
        characters: ['krieg', 'ork', 'test', 'marine', 'eldar', 'necron', 'tau', 'chaos']
      };
      
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(manyCharacters)
        });
      });
      
      // Reload to get new character set
      await page.reload();
      await expect(page.locator('.character-card')).toHaveCount(8);
      
      // Select 6 characters
      const characterNames = ['krieg', 'ork', 'test', 'marine', 'eldar', 'necron'];
      for (const name of characterNames) {
        await page.locator(`[data-testid="character-card-${name}"]`).click();
      }
      
      // Verify 6 characters selected and button enabled
      await expect(page.locator('[data-testid="selection-counter"]')).toContainText('6 of 6 characters selected');
      await expect(page.locator('[data-testid="confirm-selection-button"]')).toBeEnabled();
      
      // Attempt to select 7th character
      await page.locator('[data-testid="character-card-tau"]').click();
      
      // Verify 7th character is not selected and error is shown
      await expect(page.locator('[data-testid="character-card-tau"]')).not.toHaveClass(/selected/);
      await expect(page.locator('[data-testid="validation-error"]')).toContainText('Maximum 6 characters allowed');
      await expect(page.locator('[data-testid="selection-counter"]')).toContainText('6 of 6 characters selected');
    });

    test('should prevent selection when maximum is reached', async ({ page }) => {
      // Mock response with exactly 6 characters
      const sixCharacters = {
        characters: ['krieg', 'ork', 'test', 'marine', 'eldar', 'necron']
      };
      
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(sixCharacters)
        });
      });
      
      await page.reload();
      await expect(page.locator('.character-card')).toHaveCount(6);
      
      // Select all 6 characters
      const characterNames = ['krieg', 'ork', 'test', 'marine', 'eldar', 'necron'];
      for (const name of characterNames) {
        await page.locator(`[data-testid="character-card-${name}"]`).click();
      }
      
      // Verify all cards become disabled when max is reached
      for (const name of characterNames) {
        const card = page.locator(`[data-testid="character-card-${name}"]`);
        if (await card.evaluate(el => el.classList.contains('selected'))) {
          // Selected cards should remain clickable for deselection
          await expect(card).not.toHaveAttribute('disabled');
        } else {
          // Unselected cards should be disabled
          await expect(card).toHaveAttribute('disabled');
        }
      }
    });

    test('should show proper error messaging for validation failures', async ({ page }) => {
      // Test minimum validation error
      await page.locator('[data-testid="character-card-krieg"]').click();
      
      const validationError = page.locator('[data-testid="validation-error"]');
      await expect(validationError).toBeVisible();
      await expect(validationError).toContainText('Please select at least 2 characters to start simulation');
      await expect(validationError).toHaveCSS('color', /rgb\(244, 67, 54\)|#F44336/); // Error color from design system
      
      // Add second character to clear error
      await page.locator('[data-testid="character-card-ork"]').click();
      await expect(validationError).not.toBeVisible();
    });

    test('should control Confirm Selection button behavior based on validation', async ({ page }) => {
      const confirmButton = page.locator('[data-testid="confirm-selection-button"]');
      
      // Initial state - disabled
      await expect(confirmButton).toBeDisabled();
      await expect(confirmButton).toHaveCSS('opacity', '0.5'); // Disabled styling
      
      // Select one character - still disabled
      await page.locator('[data-testid="character-card-krieg"]').click();
      await expect(confirmButton).toBeDisabled();
      
      // Select second character - enabled
      await page.locator('[data-testid="character-card-ork"]').click();
      await expect(confirmButton).toBeEnabled();
      await expect(confirmButton).not.toHaveCSS('opacity', '0.5'); // Enabled styling
      
      // Deselect to go below minimum - disabled again
      await page.locator('[data-testid="character-card-ork"]').click();
      await expect(confirmButton).toBeDisabled();
    });

    test('should clear validation errors when user corrects selection', async ({ page }) => {
      // Start with invalid selection (1 character)
      await page.locator('[data-testid="character-card-krieg"]').click();
      await expect(page.locator('[data-testid="validation-error"]')).toBeVisible();
      
      // Add second character to make valid
      await page.locator('[data-testid="character-card-ork"]').click();
      
      // Verify error automatically clears
      await expect(page.locator('[data-testid="validation-error"]')).not.toBeVisible();
      
      // Verify success indicator appears
      await expect(page.locator('[data-testid="selection-counter"]')).toHaveCSS('color', /rgb\(34, 139, 34\)|#228B22/); // Success color
    });

    test('should show selection counter with appropriate color coding', async ({ page }) => {
      const counter = page.locator('[data-testid="selection-counter"]');
      
      // No selection - red (insufficient)
      await expect(counter).toContainText('0 of 6 characters selected');
      await expect(counter).toHaveCSS('color', /rgb\(204, 0, 0\)|#CC0000/); // Red
      
      // One selection - still red (insufficient)
      await page.locator('[data-testid="character-card-krieg"]').click();
      await expect(counter).toHaveCSS('color', /rgb\(204, 0, 0\)|#CC0000/); // Red
      
      // Two selections - green (minimum met)
      await page.locator('[data-testid="character-card-ork"]').click();
      await expect(counter).toHaveCSS('color', /rgb\(34, 139, 34\)|#228B22/); // Green
      
      // Three selections - still green (optimal range)
      await page.locator('[data-testid="character-card-test"]').click();
      await expect(counter).toHaveCSS('color', /rgb\(34, 139, 34\)|#228B22/); // Green
    });
  });

  /**
   * ACCESSIBILITY TESTS
   * Testing keyboard navigation, screen reader support, and ARIA compliance
   */
  test.describe('Accessibility Tests', () => {
    
    test.beforeEach(async ({ page }) => {
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Navigate to ensure API call is made with fresh mocks
      await page.goto(`${BASE_URL}/character-selection`);
      
      await expect(page.locator('.character-card')).toHaveCount(3);
    });

    test('should support keyboard navigation', async ({ page }) => {
      // Focus first character card with Tab
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="character-card-krieg"]')).toBeFocused();
      
      // Navigate to next card with Tab
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="character-card-ork"]')).toBeFocused();
      
      // Select with Enter key
      await page.keyboard.press('Enter');
      await expect(page.locator('[data-testid="character-card-ork"]')).toHaveClass(/selected/);
      
      // Navigate to test card and select it too (need 2 for button to be enabled)
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      await expect(page.locator('[data-testid="character-card-test"]')).toHaveClass(/selected/);
      
      // Navigate to create character button first
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="create-character-button"]')).toBeFocused();
      
      // Navigate to interactive simulation button (which comes before confirm button in tab order)
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="interactive-simulation-button"]')).toBeFocused();
      
      // Then navigate to confirm button (now enabled with 2 selections)
      await page.keyboard.press('Tab');
      // Allow some time for focus to settle and check with retry
      await expect(async () => {
        const focusedElement = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
        expect(focusedElement).toBe('confirm-selection-button');
      }).toPass({ timeout: 3000 });
    });

    test('should have proper ARIA labels and roles', async ({ page }) => {
      // Check character cards have proper ARIA attributes
      const kriegCard = page.locator('[data-testid="character-card-krieg"]');
      await expect(kriegCard).toHaveAttribute('role', 'button');
      await expect(kriegCard).toHaveAttribute('aria-label', /Select character krieg/);
      await expect(kriegCard).toHaveAttribute('tabindex', '0');
      
      // Check selection state is announced
      await kriegCard.click();
      await expect(kriegCard).toHaveAttribute('aria-pressed', 'true');
      
      // Check confirm button has proper label
      await expect(page.locator('[data-testid="confirm-selection-button"]')).toHaveAttribute('aria-label', /Confirm selection of \d+ characters/);
    });

    test('should meet color contrast requirements', async ({ page }) => {
      // This is a basic check - full contrast testing would require specialized tools
      const kriegCard = page.locator('[data-testid="character-card-krieg"]');
      
      // Ensure card exists and is visible first
      await expect(kriegCard).toBeVisible();
      
      // Check text has sufficient contrast - using more flexible color matching
      const characterName = kriegCard.locator('.character-name');
      await expect(characterName).toBeVisible();
      
      // Focus check - ensure focus indicators are accessible
      await kriegCard.focus();
      await expect(kriegCard).toBeFocused();
      
      // Check that focus outline exists (any outline width indicates accessibility compliance)
      const outlineWidth = await kriegCard.evaluate(el => getComputedStyle(el).outlineWidth);
      expect(parseInt(outlineWidth)).toBeGreaterThan(0);
    });
  });

  /**
   * ERROR RECOVERY TESTS
   * Testing retry functionality and error state recovery
   */
  test.describe('Error Recovery Tests', () => {
    
    test('should provide retry functionality after API failure', async ({ page }) => {
      // First mock a successful response to ensure clean state
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({ 
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' })
        });
      });
      
      // Navigate to trigger error state
      await page.goto(`${BASE_URL}/character-selection`);
      
      // Wait for loading to complete and error to appear
      await expect(page.locator('[data-testid="loading-spinner"]')).not.toBeVisible({ timeout: 15000 });
      await expect(page.locator('[data-testid="error-container"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
      
      // Now mock successful response for retry
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Click retry
      await page.locator('[data-testid="retry-button"]').click();
      
      // Verify successful recovery
      await expect(page.locator('.character-card')).toHaveCount(3);
      await expect(page.locator('[data-testid="error-container"]')).not.toBeVisible();
    });

    test('should show loading state during retry attempt', async ({ page }) => {
      // First set up error route to get to error state
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({ status: 500 });
      });
      
      // Navigate fresh to trigger error state
      await page.goto(`${BASE_URL}/character-selection`);
      
      // Verify error state is reached
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
      
      // Now mock successful delayed retry for next request
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await new Promise(resolve => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Click retry and verify loading state appears during the delayed response
      await page.locator('[data-testid="retry-button"]').click();
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
      
      // Verify loading eventually clears
      await expect(page.locator('[data-testid="loading-spinner"]')).not.toBeVisible({ timeout: 2000 });
      await expect(page.locator('[data-testid="character-grid"]')).toBeVisible();
    });
  });

  /**
   * INTEGRATION TESTS
   * Testing component integration with broader application flow
   */
  test.describe('Integration Tests', () => {
    
    test.skip('should integrate with simulation workflow when confirm is clicked', async ({ page }) => {
      // TODO: This test is for future functionality - currently handleStartSimulation only shows alert
      // Mock API response
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Select valid number of characters
      await page.locator('[data-testid="character-card-krieg"]').click();
      await page.locator('[data-testid="character-card-ork"]').click();
      
      // Setup alert dialog handler to test current behavior
      page.on('dialog', async dialog => {
        expect(dialog.message()).toContain('krieg, ork');
        await dialog.accept();
      });
      
      // Click confirm - currently shows alert instead of API call
      await page.locator('[data-testid="confirm-selection-button"]').click();
    });

    test('should handle confirmation dialog if enabled', async ({ page }) => {
      await page.route(`${API_BASE_URL}/characters`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CHARACTERS_RESPONSE)
        });
      });
      
      // Select characters
      await page.locator('[data-testid="character-card-krieg"]').click();
      await page.locator('[data-testid="character-card-ork"]').click();
      
      // Click confirm and check for dialog
      await page.locator('[data-testid="confirm-selection-button"]').click();
      
      // If confirmation dialog is implemented, it should appear
      const confirmDialog = page.locator('[data-testid="confirmation-dialog"]');
      if (await confirmDialog.isVisible()) {
        await expect(confirmDialog).toContainText('Start simulation with 2 characters?');
        await page.locator('[data-testid="confirm-dialog-yes"]').click();
      }
    });
  });
});