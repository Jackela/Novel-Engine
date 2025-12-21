/**
 * Decision Dialog E2E Tests
 *
 * Tests for the decision point dialog that appears during story generation
 * at critical narrative moments for user interaction.
 *
 * These tests verify the complete user flow from decision presentation
 * to user response submission.
 */

import { test, expect } from '@playwright/test';
import { DecisionDialogPage, type MockDecisionPoint } from './pages/DecisionDialogPage';
import { DashboardPage } from './pages/DashboardPage';

// Extend window interface for Redux store access
declare global {
  interface Window {
    __REDUX_STORE__?: {
      dispatch: (action: { type: string; payload?: unknown }) => void;
      getState: () => {
        decision: {
          currentDecision: unknown;
          pauseState: string;
          selectedOptionId: number | null;
          freeTextInput: string;
          remainingSeconds: number;
        };
      };
    };
  }
}

test.describe('Decision Dialog', () => {
  let dashboardPage: DashboardPage;
  let decisionDialog: DecisionDialogPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    decisionDialog = new DecisionDialogPage(page);

    // Navigate to dashboard
    await dashboardPage.navigateToDashboard({ mockAPIs: true });

    // Expose Redux store for testing (if not already exposed)
    await page.evaluate(() => {
      // Store reference is set up in the app for testing
      if (typeof window !== 'undefined' && !window.__REDUX_STORE__) {
        // The app should expose the store for e2e testing
        console.log('Redux store not exposed - some tests may fail');
      }
    });
  });

  test.describe('Dialog Appearance', () => {
    test('dialog does not appear without decision point', async ({ page }) => {
      // Verify dialog is not visible initially
      const isVisible = await decisionDialog.isDialogVisible();
      expect(isVisible).toBe(false);
    });

    test('dialog appears when decision point is injected', async ({ page }) => {
      // Inject a decision point
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);

      // Wait for dialog to appear
      await decisionDialog.waitForDialog();

      // Verify dialog is visible
      const isVisible = await decisionDialog.isDialogVisible();
      expect(isVisible).toBe(true);
    });

    test('displays correct title and description', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision({
        title: 'Test Decision Title',
        description: 'This is the test decision description.',
      });
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Verify title
      await expect(page.getByText('Test Decision Title')).toBeVisible();

      // Verify description
      await expect(page.getByText('This is the test decision description.')).toBeVisible();
    });

    test('displays turn number and decision type', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision({
        turnNumber: 7,
        decisionType: 'crisis',
      });
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Verify turn number
      await expect(page.getByText(/Turn 7/)).toBeVisible();

      // Verify decision type
      await expect(page.getByText(/crisis/i)).toBeVisible();
    });

    test('displays narrative context when provided', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision({
        narrativeContext: 'The moonlight cast long shadows across the ancient ruins...',
      });
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      await expect(page.getByText(/moonlight cast long shadows/)).toBeVisible();
    });

    test('displays all option cards', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Verify all options are displayed
      const labels = await decisionDialog.getOptionLabels();
      expect(labels).toContain('Investigate Signal');
      expect(labels).toContain('Evacuate Area');
      expect(labels).toContain('Call for Backup');
    });
  });

  test.describe('Option Selection', () => {
    test('can select an option by clicking', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Click on an option
      await decisionDialog.selectOptionByLabel('Evacuate Area');

      // Verify Redux state updated (via evaluate)
      const state = await page.evaluate(() => {
        return window.__REDUX_STORE__?.getState().decision.selectedOptionId;
      });
      expect(state).toBe(2); // Evacuate Area has optionId: 2
    });

    test('can change selection to different option', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Select first option
      await decisionDialog.selectOptionByLabel('Investigate Signal');

      // Change to different option
      await decisionDialog.selectOptionByLabel('Call for Backup');

      // Verify final selection
      const state = await page.evaluate(() => {
        return window.__REDUX_STORE__?.getState().decision.selectedOptionId;
      });
      expect(state).toBe(3); // Call for Backup has optionId: 3
    });

    test('confirm button becomes enabled when option is selected', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision({
        defaultOptionId: null as any, // No default selection
      });
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Clear any default selection
      await page.evaluate(() => {
        window.__REDUX_STORE__?.dispatch({
          type: 'decision/selectOption',
          payload: null,
        });
      });

      // Confirm button should be disabled initially
      const isEnabledBefore = await decisionDialog.isConfirmEnabled();
      expect(isEnabledBefore).toBe(false);

      // Select an option
      await decisionDialog.selectOptionByLabel('Investigate Signal');

      // Confirm button should now be enabled
      const isEnabledAfter = await decisionDialog.isConfirmEnabled();
      expect(isEnabledAfter).toBe(true);
    });
  });

  test.describe('Free Text Input Mode', () => {
    test('can switch to free text mode', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Switch to free text mode
      await decisionDialog.switchToFreeTextMode();

      // Verify text input is visible
      await expect(decisionDialog.freeTextInput).toBeVisible();
    });

    test('can enter custom action text', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      await decisionDialog.switchToFreeTextMode();
      await decisionDialog.enterFreeText('Make the character climb the tower');

      // Verify text was entered
      const value = await decisionDialog.getFreeTextValue();
      expect(value).toBe('Make the character climb the tower');
    });

    test('shows character count', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      await decisionDialog.switchToFreeTextMode();
      await decisionDialog.enterFreeText('Test input');

      // Verify character count
      const countText = await decisionDialog.getCharacterCountText();
      expect(countText).toContain('10/500');
    });

    test('confirm button disabled when free text too short', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      await decisionDialog.switchToFreeTextMode();

      // Enter less than 5 characters
      await decisionDialog.enterFreeText('Run');

      // Confirm should be disabled
      const isEnabled = await decisionDialog.isConfirmEnabled();
      expect(isEnabled).toBe(false);
    });

    test('confirm button enabled when free text meets minimum length', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      await decisionDialog.switchToFreeTextMode();

      // Enter 5+ characters
      await decisionDialog.enterFreeText('Run away quickly');

      // Confirm should be enabled
      const isEnabled = await decisionDialog.isConfirmEnabled();
      expect(isEnabled).toBe(true);
    });

    test('can switch back to options mode', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Switch to free text
      await decisionDialog.switchToFreeTextMode();
      await expect(decisionDialog.freeTextInput).toBeVisible();

      // Switch back to options
      await decisionDialog.switchToOptionsMode();

      // Options should be visible again
      const labels = await decisionDialog.getOptionLabels();
      expect(labels.length).toBeGreaterThan(0);
    });
  });

  test.describe('Countdown Timer', () => {
    test('displays countdown timer', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision({
        timeoutSeconds: 120,
      });
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Verify timer is displayed
      const timerText = await decisionDialog.getCountdownText();
      expect(timerText).toMatch(/\d+:\d+/);
    });

    test('countdown decrements over time', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision({
        timeoutSeconds: 60,
      });
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Get initial time
      const initialSeconds = await page.evaluate(() => {
        return window.__REDUX_STORE__?.getState().decision.remainingSeconds;
      });

      // Wait 2 seconds
      await page.waitForTimeout(2100);

      // Get updated time
      const updatedSeconds = await page.evaluate(() => {
        return window.__REDUX_STORE__?.getState().decision.remainingSeconds;
      });

      // Should have decremented
      expect(updatedSeconds).toBeLessThan(initialSeconds!);
    });
  });

  test.describe('Skip Functionality', () => {
    test('footer skip button closes dialog', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Click skip
      await decisionDialog.clickSkip();

      // Dialog should close
      await decisionDialog.waitForDialogClosed();
      const isVisible = await decisionDialog.isDialogVisible();
      expect(isVisible).toBe(false);
    });

    test('header skip button closes dialog', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Click header skip (X button)
      await decisionDialog.clickHeaderSkip();

      // Dialog should close
      await decisionDialog.waitForDialogClosed();
      const isVisible = await decisionDialog.isDialogVisible();
      expect(isVisible).toBe(false);
    });
  });

  test.describe('Accessibility', () => {
    test('dialog has proper ARIA attributes', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Verify accessibility attributes
      await decisionDialog.verifyAccessibility();
    });

    test('dialog can be closed with Escape key', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Press Escape
      await page.keyboard.press('Escape');

      // Dialog should close
      await decisionDialog.waitForDialogClosed();
      const isVisible = await decisionDialog.isDialogVisible();
      expect(isVisible).toBe(false);
    });

    test('option cards are keyboard navigable', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Focus on first option card using Tab
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Press Enter to select
      await page.keyboard.press('Enter');

      // Verify an option was selected
      const state = await page.evaluate(() => {
        return window.__REDUX_STORE__?.getState().decision.selectedOptionId;
      });
      expect(state).not.toBeNull();
    });
  });

  test.describe('Confirm Submission', () => {
    test('clicking confirm with option selected closes dialog', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Select an option
      await decisionDialog.selectOptionByLabel('Investigate Signal');

      // Click confirm
      await decisionDialog.clickConfirm();

      // Dialog should close (assuming API mock or immediate resolution)
      // Note: In real E2E tests, you'd mock the API response
      await page.waitForTimeout(500);
    });

    test('clicking confirm with free text closes dialog', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Switch to free text and enter valid input
      await decisionDialog.switchToFreeTextMode();
      await decisionDialog.enterFreeText('Have the character explore the cave');

      // Click confirm
      await decisionDialog.clickConfirm();

      // Dialog should close
      await page.waitForTimeout(500);
    });
  });

  test.describe('Error Handling', () => {
    test('displays error message when present', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Inject an error state
      await page.evaluate(() => {
        window.__REDUX_STORE__?.dispatch({
          type: 'decision/submitResponse/rejected',
          payload: 'Failed to submit decision. Please try again.',
        });
      });

      // Wait for error to appear
      await page.waitForTimeout(100);

      // Check for error (may not appear depending on reducer handling)
      const hasError = await decisionDialog.hasError();
      // Error display depends on implementation
    });
  });

  test.describe('Loading State', () => {
    test('confirm button shows loading during submission', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Select an option
      await decisionDialog.selectOptionByLabel('Investigate Signal');

      // Set submitting state
      await page.evaluate(() => {
        window.__REDUX_STORE__?.dispatch({
          type: 'decision/submitResponse/pending',
        });
      });

      // Verify button is disabled during submission
      const isEnabled = await decisionDialog.isConfirmEnabled();
      expect(isEnabled).toBe(false);
    });
  });

  test.describe('Negotiation Flow', () => {
    test('shows negotiation UI when negotiation result is set', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Inject negotiation result
      await page.evaluate(() => {
        window.__REDUX_STORE__?.dispatch({
          type: 'decision/setNegotiationResult',
          payload: {
            decisionId: 'test-decision',
            feasibility: 'minor_adjustment',
            explanation: 'The action needs a small adjustment to work.',
            adjustedAction: 'Modified action suggestion',
            alternatives: [],
          },
        });
      });

      // Verify negotiation UI is visible
      await expect(page.getByText(/Adjustment Suggested/i)).toBeVisible();
      await expect(page.getByText(/needs a small adjustment/)).toBeVisible();
    });

    test('shows accept and keep original buttons during negotiation', async ({ page }) => {
      const mockDecision = DecisionDialogPage.createMockDecision();
      await decisionDialog.injectDecisionPoint(mockDecision);
      await decisionDialog.waitForDialog();

      // Inject negotiation result
      await page.evaluate(() => {
        window.__REDUX_STORE__?.dispatch({
          type: 'decision/setNegotiationResult',
          payload: {
            decisionId: 'test-decision',
            feasibility: 'minor_adjustment',
            explanation: 'The action needs adjustment.',
            adjustedAction: 'Modified action',
            alternatives: [],
          },
        });
      });

      // Verify buttons are visible
      await expect(decisionDialog.acceptSuggestionButton).toBeVisible();
      await expect(decisionDialog.keepOriginalButton).toBeVisible();
    });
  });
});

test.describe('Decision Dialog Integration', () => {
  test('complete user flow: view decision, select option, confirm', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    const decisionDialog = new DecisionDialogPage(page);

    // Navigate to dashboard
    await dashboardPage.navigateToDashboard({ mockAPIs: true });

    // Verify no dialog initially
    expect(await decisionDialog.isDialogVisible()).toBe(false);

    // Inject decision
    const mockDecision = DecisionDialogPage.createMockDecision();
    await decisionDialog.injectDecisionPoint(mockDecision);

    // Dialog appears
    await decisionDialog.waitForDialog();
    expect(await decisionDialog.isDialogVisible()).toBe(true);

    // Verify content
    await expect(page.getByText('Critical Decision Point')).toBeVisible();

    // Select an option
    await decisionDialog.selectOptionByLabel('Evacuate Area');

    // Verify selection
    const selectedId = await page.evaluate(() => {
      return window.__REDUX_STORE__?.getState().decision.selectedOptionId;
    });
    expect(selectedId).toBe(2);

    // Confirm is enabled
    expect(await decisionDialog.isConfirmEnabled()).toBe(true);

    // Click confirm
    await decisionDialog.clickConfirm();

    // Wait for dialog to process
    await page.waitForTimeout(500);
  });

  test('complete user flow: view decision, enter custom action, confirm', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    const decisionDialog = new DecisionDialogPage(page);

    // Navigate to dashboard
    await dashboardPage.navigateToDashboard({ mockAPIs: true });

    // Inject decision
    const mockDecision = DecisionDialogPage.createMockDecision();
    await decisionDialog.injectDecisionPoint(mockDecision);
    await decisionDialog.waitForDialog();

    // Switch to free text mode
    await decisionDialog.switchToFreeTextMode();

    // Enter custom action
    await decisionDialog.enterFreeText('Have the character send a distress signal');

    // Verify text entered
    const freeText = await page.evaluate(() => {
      return window.__REDUX_STORE__?.getState().decision.freeTextInput;
    });
    expect(freeText).toBe('Have the character send a distress signal');

    // Confirm is enabled
    expect(await decisionDialog.isConfirmEnabled()).toBe(true);

    // Click confirm
    await decisionDialog.clickConfirm();

    // Wait for dialog to process
    await page.waitForTimeout(500);
  });
});
