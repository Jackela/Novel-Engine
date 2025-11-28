/**
 * DecisionDialogPage - Page Object Model for Decision Point Dialog
 *
 * Provides methods to interact with the decision dialog that appears
 * during story generation at critical narrative moments.
 */

import { type Page, type Locator, expect } from '@playwright/test';

export interface MockDecisionPoint {
  decisionId: string;
  decisionType: string;
  turnNumber: number;
  title: string;
  description: string;
  narrativeContext?: string;
  options: Array<{
    optionId: number;
    label: string;
    description: string;
    icon?: string;
    impactPreview?: string;
  }>;
  defaultOptionId?: number;
  timeoutSeconds: number;
  dramaticTension?: number;
  emotionalIntensity?: number;
}

export class DecisionDialogPage {
  readonly page: Page;

  // Dialog container
  readonly dialog: Locator;
  readonly dialogTitle: Locator;
  readonly dialogDescription: Locator;

  // Header elements
  readonly turnChip: Locator;
  readonly decisionTypeChip: Locator;
  readonly countdownTimer: Locator;
  readonly headerSkipButton: Locator;

  // Content elements
  readonly narrativeContext: Locator;
  readonly errorAlert: Locator;

  // Input mode buttons
  readonly chooseOptionButton: Locator;
  readonly customActionButton: Locator;

  // Options grid
  readonly optionCards: Locator;

  // Free text input
  readonly freeTextInput: Locator;
  readonly characterCount: Locator;

  // Negotiation elements
  readonly negotiationAlert: Locator;
  readonly acceptSuggestionButton: Locator;
  readonly keepOriginalButton: Locator;

  // Footer buttons
  readonly footerSkipButton: Locator;
  readonly confirmButton: Locator;

  constructor(page: Page) {
    this.page = page;

    // Dialog container
    this.dialog = page.getByRole('dialog');
    this.dialogTitle = page.locator('[id="decision-dialog-title"]');
    this.dialogDescription = page.locator('[id="decision-dialog-description"]');

    // Header elements
    this.turnChip = page.getByText(/Turn \d+/);
    this.decisionTypeChip = page.locator('.MuiChip-root').filter({ hasText: /choice|turning|crisis|climax/i });
    this.countdownTimer = page.locator('[class*="MuiBox"]').filter({ has: page.locator('[data-testid="TimerIcon"], svg') }).first();
    this.headerSkipButton = page.getByRole('button', { name: /skip decision/i });

    // Content elements
    this.narrativeContext = page.locator('[class*="borderLeft"]').first();
    this.errorAlert = page.getByRole('alert').filter({ hasText: /error|failed/i });

    // Input mode buttons
    this.chooseOptionButton = page.getByRole('button', { name: /choose option/i });
    this.customActionButton = page.getByRole('button', { name: /custom action/i });

    // Options grid
    this.optionCards = page.locator('.MuiCard-root button');

    // Free text input
    this.freeTextInput = page.getByPlaceholder(/describe what you want/i);
    this.characterCount = page.getByText(/\/500/);

    // Negotiation elements
    this.negotiationAlert = page.getByRole('alert').filter({ hasText: /adjustment|accepted|alternatives/i });
    this.acceptSuggestionButton = page.getByRole('button', { name: /accept suggestion/i });
    this.keepOriginalButton = page.getByRole('button', { name: /keep original/i });

    // Footer buttons
    this.footerSkipButton = page.getByRole('button', { name: /skip.*default/i });
    this.confirmButton = page.getByRole('button', { name: /confirm/i });
  }

  /**
   * Wait for the decision dialog to appear
   */
  async waitForDialog(timeout = 10000): Promise<void> {
    await this.dialog.waitFor({ state: 'visible', timeout });
  }

  /**
   * Wait for the decision dialog to close
   */
  async waitForDialogClosed(timeout = 10000): Promise<void> {
    await this.dialog.waitFor({ state: 'hidden', timeout });
  }

  /**
   * Check if the dialog is visible
   */
  async isDialogVisible(): Promise<boolean> {
    return this.dialog.isVisible();
  }

  /**
   * Get the dialog title text
   */
  async getTitle(): Promise<string> {
    return this.dialogTitle.textContent() || '';
  }

  /**
   * Get the dialog description text
   */
  async getDescription(): Promise<string> {
    return this.dialogDescription.textContent() || '';
  }

  /**
   * Get the turn number from the chip
   */
  async getTurnNumber(): Promise<number | null> {
    const text = await this.turnChip.textContent();
    const match = text?.match(/Turn (\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  /**
   * Get the countdown timer text
   */
  async getCountdownText(): Promise<string> {
    const timerContainer = this.page.locator('[class*="MuiBox"]').filter({
      hasText: /\d+:\d+/
    }).first();
    const text = await timerContainer.textContent();
    return text?.match(/\d+:\d+/)?.[0] || '';
  }

  /**
   * Get all option card labels
   */
  async getOptionLabels(): Promise<string[]> {
    const cards = this.optionCards;
    const count = await cards.count();
    const labels: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await cards.nth(i).locator('.MuiTypography-subtitle1').textContent();
      if (text) labels.push(text);
    }

    return labels;
  }

  /**
   * Select an option by its label
   */
  async selectOptionByLabel(label: string): Promise<void> {
    const card = this.optionCards.filter({ hasText: label });
    await card.click();
  }

  /**
   * Select an option by index (0-based)
   */
  async selectOptionByIndex(index: number): Promise<void> {
    await this.optionCards.nth(index).click();
  }

  /**
   * Check if an option is selected by its label
   */
  async isOptionSelected(label: string): Promise<boolean> {
    const card = this.optionCards.filter({ hasText: label }).locator('..');
    const classes = await card.getAttribute('class');
    // Selected cards have elevation variant or different border
    return classes?.includes('elevation') || false;
  }

  /**
   * Switch to free text input mode
   */
  async switchToFreeTextMode(): Promise<void> {
    await this.customActionButton.click();
    await this.freeTextInput.waitFor({ state: 'visible' });
  }

  /**
   * Switch to options mode
   */
  async switchToOptionsMode(): Promise<void> {
    await this.chooseOptionButton.click();
  }

  /**
   * Enter free text input
   */
  async enterFreeText(text: string): Promise<void> {
    await this.freeTextInput.fill(text);
  }

  /**
   * Get the current free text input value
   */
  async getFreeTextValue(): Promise<string> {
    return this.freeTextInput.inputValue();
  }

  /**
   * Get the character count display
   */
  async getCharacterCountText(): Promise<string> {
    return await this.characterCount.textContent() || '';
  }

  /**
   * Click the confirm button
   */
  async clickConfirm(): Promise<void> {
    await this.confirmButton.click();
  }

  /**
   * Click the skip button (footer)
   */
  async clickSkip(): Promise<void> {
    await this.footerSkipButton.click();
  }

  /**
   * Click the header skip button (X icon)
   */
  async clickHeaderSkip(): Promise<void> {
    await this.headerSkipButton.click();
  }

  /**
   * Check if confirm button is enabled
   */
  async isConfirmEnabled(): Promise<boolean> {
    return this.confirmButton.isEnabled();
  }

  /**
   * Check if dialog shows negotiation UI
   */
  async isNegotiationVisible(): Promise<boolean> {
    return this.negotiationAlert.isVisible();
  }

  /**
   * Accept the negotiation suggestion
   */
  async acceptNegotiation(): Promise<void> {
    await this.acceptSuggestionButton.click();
  }

  /**
   * Keep original action (insist)
   */
  async keepOriginal(): Promise<void> {
    await this.keepOriginalButton.click();
  }

  /**
   * Check if error is displayed
   */
  async hasError(): Promise<boolean> {
    return this.errorAlert.isVisible();
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string> {
    if (await this.hasError()) {
      return await this.errorAlert.textContent() || '';
    }
    return '';
  }

  /**
   * Verify dialog has proper accessibility attributes
   */
  async verifyAccessibility(): Promise<void> {
    await expect(this.dialog).toHaveAttribute('aria-labelledby', 'decision-dialog-title');
    await expect(this.dialog).toHaveAttribute('aria-describedby', 'decision-dialog-description');
  }

  /**
   * Inject a mock decision point via Redux store
   * This simulates receiving a decision_required SSE event
   */
  async injectDecisionPoint(decision: MockDecisionPoint): Promise<void> {
    const now = Date.now();
    const decisionData = {
      ...decision,
      createdAt: new Date(now).toISOString(),
      expiresAt: new Date(now + decision.timeoutSeconds * 1000).toISOString(),
      dramaticTension: decision.dramaticTension ?? 7,
      emotionalIntensity: decision.emotionalIntensity ?? 7,
    };

    await this.page.evaluate((data) => {
      // Access Redux store and dispatch setDecisionPoint
      const store = (window as unknown as { __REDUX_STORE__?: { dispatch: (action: unknown) => void } }).__REDUX_STORE__;
      if (store) {
        store.dispatch({
          type: 'decision/setDecisionPoint',
          payload: data,
        });
      }
    }, decisionData);
  }

  /**
   * Create a standard mock decision point for testing
   */
  static createMockDecision(overrides: Partial<MockDecisionPoint> = {}): MockDecisionPoint {
    return {
      decisionId: `test-decision-${Date.now()}`,
      decisionType: 'character_choice',
      turnNumber: 5,
      title: 'Critical Decision Point',
      description: 'The story has reached a pivotal moment. Choose how the characters should proceed.',
      narrativeContext: 'Aria stands at the crossroads of the Meridian Station, facing an unknown threat...',
      options: [
        {
          optionId: 1,
          label: 'Investigate Signal',
          description: 'Proceed with caution to investigate the mysterious signal',
          icon: '🔍',
          impactPreview: 'May reveal hidden information',
        },
        {
          optionId: 2,
          label: 'Evacuate Area',
          description: 'Prioritize safety and evacuate the area immediately',
          icon: '⚠️',
          impactPreview: 'Ensures character safety',
        },
        {
          optionId: 3,
          label: 'Call for Backup',
          description: 'Request additional support before proceeding',
          icon: '📡',
          impactPreview: 'Delays action but increases resources',
        },
      ],
      defaultOptionId: 1,
      timeoutSeconds: 120,
      ...overrides,
    };
  }
}
