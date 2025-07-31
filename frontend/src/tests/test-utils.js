/**
 * Test Utilities for Character Selection Component Tests
 * 
 * This file provides helper functions and constants for testing
 * the Character Selection Component functionality.
 */

// Mock data constants
export const MOCK_CHARACTERS_RESPONSE = {
  characters: ['krieg', 'ork', 'test']
};

export const MOCK_CHARACTER_DETAILS = {
  krieg: {
    character_name: 'krieg',
    narrative_context: 'Trooper 86 of the Death Korps of Krieg stands ready for the Emperor\'s will. Born into a world of perpetual war and sacrifice, this Guardsman embodies the grim determination and fatalistic devotion that defines his regiment.',
    structured_data: {
      name: 'Trooper 86',
      factions: ['Astra Militarum', 'Death Korps of Krieg'],
      personality_traits: ['Fatalistic', 'Grim', 'Loyal to the Emperor'],
      equipment: ['Lasgun', 'Flak Armor', 'Entrenching Tool'],
      background: 'Death World Survivor'
    },
    file_count: { md: 1, yaml: 1 }
  },
  ork: {
    character_name: 'ork',
    narrative_context: 'WAAAGH! Boss Skarfang of the Blood Axes leads his boyz with cunning brutality. Unlike other Ork clans, the Blood Axes have learned from their enemies, adopting tactics that make them unpredictable and dangerous.',
    structured_data: {
      name: 'Boss Skarfang',
      factions: ['Orks', 'Blood Axes'],
      personality_traits: ['Aggressive', 'Cunning', 'Brutal'],
      equipment: ['Big Choppa', 'Slugga', 'Heavy Armor'],
      background: 'Clan Boss'
    },
    file_count: { md: 1, yaml: 1 }
  },
  test: {
    character_name: 'test',
    narrative_context: 'Test character for development and validation purposes. This character serves as a placeholder for testing various system functionalities.',
    structured_data: {
      name: 'Test Character',
      factions: ['Test Faction'],
      personality_traits: ['Testing', 'Placeholder', 'Development'],
      equipment: ['Test Equipment'],
      background: 'Testing Environment'
    },
    file_count: { md: 1, yaml: 1 }
  }
};

// Extended mock data for testing maximum selection limits
export const EXTENDED_CHARACTERS_RESPONSE = {
  characters: ['krieg', 'ork', 'test', 'marine', 'eldar', 'necron', 'tau', 'chaos']
};

// API configuration constants
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000',
  TIMEOUT: 5000,
  ENDPOINTS: {
    CHARACTERS: '/characters',
    CHARACTER_DETAIL: '/characters',
    SIMULATION_START: '/simulation/start',
    HEALTH: '/health'
  }
};

// Test data selectors (data-testid values)
export const SELECTORS = {
  // Loading states
  LOADING_SPINNER: '[data-testid="loading-spinner"]',
  CHARACTER_GRID: '[data-testid="character-grid"]',
  
  // Character cards
  CHARACTER_CARD: '[data-testid="character-card"]',
  CHARACTER_CARD_KRIEG: '[data-testid="character-card-krieg"]',
  CHARACTER_CARD_ORC: '[data-testid="character-card-ork"]',
  CHARACTER_CARD_TEST: '[data-testid="character-card-test"]',
  
  // Selection indicators
  SELECTION_CHECKMARK: (character) => `[data-testid="selection-checkmark-${character}"]`,
  SELECTION_COUNTER: '[data-testid="selection-counter"]',
  
  // Buttons
  CONFIRM_SELECTION_BUTTON: '[data-testid="confirm-selection-button"]',
  RETRY_BUTTON: '[data-testid="retry-button"]',
  
  // Error states
  ERROR_MESSAGE: '[data-testid="error-message"]',
  VALIDATION_ERROR: '[data-testid="validation-error"]',
  
  // Dialogs
  CONFIRMATION_DIALOG: '[data-testid="confirmation-dialog"]',
  CONFIRM_DIALOG_YES: '[data-testid="confirm-dialog-yes"]',
  CONFIRM_DIALOG_NO: '[data-testid="confirm-dialog-no"]'
};

// Validation constants
export const VALIDATION_LIMITS = {
  MIN_CHARACTERS: 2,
  MAX_CHARACTERS: 6
};

// Error messages (should match component implementation)
export const ERROR_MESSAGES = {
  MIN_SELECTION: 'Please select at least 2 characters to start simulation',
  MAX_SELECTION: 'Maximum 6 characters allowed',
  SERVER_ERROR: 'Server error - Please try again later',
  NOT_FOUND: 'No characters found - Please ensure character data is available',
  NETWORK_ERROR: 'Cannot connect to server - Please ensure the backend is running',
  TIMEOUT: 'Request timeout - Server may be slow to respond'
};

// Helper functions for common test operations
export class TestHelpers {
  /**
   * Mock successful API response for characters
   * @param {Page} page - Playwright page object
   * @param {Object} charactersData - Optional custom characters data
   */
  static async mockCharactersAPI(page, charactersData = MOCK_CHARACTERS_RESPONSE) {
    await page.route(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHARACTERS}`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(charactersData)
      });
    });
  }

  /**
   * Mock API error response
   * @param {Page} page - Playwright page object
   * @param {number} status - HTTP status code
   * @param {string} message - Error message
   */
  static async mockAPIError(page, status = 500, message = 'Internal server error') {
    await page.route(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHARACTERS}`, async route => {
      await route.fulfill({
        status: status,
        contentType: 'application/json',
        body: JSON.stringify({ detail: message })
      });
    });
  }

  /**
   * Mock network failure
   * @param {Page} page - Playwright page object
   */
  static async mockNetworkFailure(page) {
    await page.route(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHARACTERS}`, async route => {
      await route.abort('failed');
    });
  }

  /**
   * Select multiple characters by their names
   * @param {Page} page - Playwright page object
   * @param {Array<string>} characterNames - Array of character names to select
   */
  static async selectCharacters(page, characterNames) {
    for (const name of characterNames) {
      await page.locator(`[data-testid="character-card-${name}"]`).click();
    }
  }

  /**
   * Wait for characters to load and verify count
   * @param {Page} page - Playwright page object
   * @param {number} expectedCount - Expected number of character cards
   */
  static async waitForCharactersToLoad(page, expectedCount = 3) {
    await page.waitForSelector(SELECTORS.CHARACTER_CARD);
    await page.locator(SELECTORS.CHARACTER_CARD).count().then(count => {
      if (count !== expectedCount) {
        throw new Error(`Expected ${expectedCount} characters, but found ${count}`);
      }
    });
  }

  /**
   * Verify selection state of a character
   * @param {Page} page - Playwright page object
   * @param {string} characterName - Name of the character
   * @param {boolean} shouldBeSelected - Whether character should be selected
   */
  static async verifySelectionState(page, characterName, shouldBeSelected) {
    const card = page.locator(`[data-testid="character-card-${characterName}"]`);
    const checkmark = page.locator(SELECTORS.SELECTION_CHECKMARK(characterName));
    
    if (shouldBeSelected) {
      await expect(card).toHaveClass(/selected/);
      await expect(checkmark).toBeVisible();
    } else {
      await expect(card).not.toHaveClass(/selected/);
      await expect(checkmark).not.toBeVisible();
    }
  }

  /**
   * Verify selection counter displays correct count and color
   * @param {Page} page - Playwright page object
   * @param {number} count - Expected selection count
   * @param {string} expectedColor - Expected color (red, green)
   */
  static async verifySelectionCounter(page, count, expectedColor = null) {
    const counter = page.locator(SELECTORS.SELECTION_COUNTER);
    await expect(counter).toContainText(`${count} of ${VALIDATION_LIMITS.MAX_CHARACTERS} characters selected`);
    
    if (expectedColor) {
      const colorMap = {
        red: '#CC0000',
        green: '#228B22',
        yellow: '#FFD700'
      };
      await expect(counter).toHaveCSS('color', colorMap[expectedColor]);
    }
  }

  /**
   * Verify confirm button state
   * @param {Page} page - Playwright page object
   * @param {boolean} shouldBeEnabled - Whether button should be enabled
   */
  static async verifyConfirmButtonState(page, shouldBeEnabled) {
    const button = page.locator(SELECTORS.CONFIRM_SELECTION_BUTTON);
    
    if (shouldBeEnabled) {
      await expect(button).toBeEnabled();
      await expect(button).not.toHaveCSS('opacity', '0.5');
    } else {
      await expect(button).toBeDisabled();
      await expect(button).toHaveCSS('opacity', '0.5');
    }
  }

  /**
   * Verify validation error message
   * @param {Page} page - Playwright page object
   * @param {string} expectedMessage - Expected error message
   * @param {boolean} shouldBeVisible - Whether error should be visible
   */
  static async verifyValidationError(page, expectedMessage = null, shouldBeVisible = true) {
    const errorElement = page.locator(SELECTORS.VALIDATION_ERROR);
    
    if (shouldBeVisible && expectedMessage) {
      await expect(errorElement).toBeVisible();
      await expect(errorElement).toContainText(expectedMessage);
      await expect(errorElement).toHaveCSS('color', '#CC0000'); // Error color
    } else {
      await expect(errorElement).not.toBeVisible();
    }
  }
}

// Performance testing helpers
export class PerformanceHelpers {
  /**
   * Measure component load time
   * @param {Page} page - Playwright page object
   * @returns {Promise<number>} Load time in milliseconds
   */
  static async measureLoadTime(page) {
    const startTime = Date.now();
    await page.waitForSelector(SELECTORS.CHARACTER_GRID);
    const endTime = Date.now();
    return endTime - startTime;
  }

  /**
   * Measure selection response time
   * @param {Page} page - Playwright page object
   * @param {string} characterName - Character to select
   * @returns {Promise<number>} Response time in milliseconds
   */
  static async measureSelectionResponseTime(page, characterName) {
    const startTime = Date.now();
    await page.locator(`[data-testid="character-card-${characterName}"]`).click();
    await page.locator(SELECTORS.SELECTION_CHECKMARK(characterName)).waitFor();
    const endTime = Date.now();
    return endTime - startTime;
  }
}

// Accessibility testing helpers
export class AccessibilityHelpers {
  /**
   * Test keyboard navigation through character cards
   * @param {Page} page - Playwright page object
   */
  static async testKeyboardNavigation(page) {
    // Start from first focusable element
    await page.keyboard.press('Tab');
    
    // Verify first card is focused
    await expect(page.locator(SELECTORS.CHARACTER_CARD).first()).toBeFocused();
    
    // Navigate through cards
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Navigate to confirm button
    await page.keyboard.press('Tab');
    await expect(page.locator(SELECTORS.CONFIRM_SELECTION_BUTTON)).toBeFocused();
  }

  /**
   * Verify ARIA attributes are properly set
   * @param {Page} page - Playwright page object
   * @param {string} characterName - Character to check
   */
  static async verifyARIAAttributes(page, characterName) {
    const card = page.locator(`[data-testid="character-card-${characterName}"]`);
    
    // Check required ARIA attributes
    await expect(card).toHaveAttribute('role', 'button');
    await expect(card).toHaveAttribute('tabindex', '0');
    await expect(card).toHaveAttribute('aria-label');
    
    // Check selection state is announced
    const isSelected = await card.evaluate(el => el.classList.contains('selected'));
    await expect(card).toHaveAttribute('aria-pressed', isSelected.toString());
  }
}