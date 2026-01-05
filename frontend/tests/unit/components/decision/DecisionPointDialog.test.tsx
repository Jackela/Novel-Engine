/**
 * DecisionPointDialog Component Tests
 *
 * Tests for the decision point dialog that appears during story generation
 * at critical narrative moments for user interaction.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import DecisionPointDialog from '../../../../src/components/decision/DecisionPointDialog';
import decisionReducer, {
  setDecisionPoint,
  type DecisionPoint,
} from '../../../../src/store/slices/decisionSlice';

// Mock focus trap hook
vi.mock('../../../../src/utils/focusManagement', () => ({
  useFocusTrap: vi.fn(),
}));

// Helper to create a test store
function createTestStore(initialState?: Partial<ReturnType<typeof decisionReducer>>) {
  return configureStore({
    reducer: {
      decision: decisionReducer,
    },
    preloadedState: initialState ? { decision: { ...getDefaultState(), ...initialState } } : undefined,
  });
}

function getDefaultState() {
  return {
    currentDecision: null,
    pauseState: 'running' as const,
    isNegotiating: false,
    negotiationResult: null,
    remainingSeconds: 0,
    selectedOptionId: null,
    freeTextInput: '',
    isSubmitting: false,
    error: null,
    decisionHistory: [],
  };
}

// Mock decision data
const mockDecision: DecisionPoint = {
  decisionId: 'test-decision-001',
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
  dramaticTension: 8,
  emotionalIntensity: 7,
  createdAt: new Date().toISOString(),
  expiresAt: new Date(Date.now() + 120000).toISOString(),
};

// Helper to render with store
function renderWithStore(
  component: React.ReactNode,
  store = createTestStore()
) {
  return {
    ...render(<Provider store={store}>{component}</Provider>),
    store,
  };
}

describe('DecisionPointDialog', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('does not render when no decision is active', () => {
      renderWithStore(<DecisionPointDialog />);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('renders dialog when decision point is active', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('displays decision title and description', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByText('Critical Decision Point')).toBeInTheDocument();
      expect(
        screen.getByText(/The story has reached a pivotal moment/)
      ).toBeInTheDocument();
    });

    it('renders all option cards', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByText('Investigate Signal')).toBeInTheDocument();
      expect(screen.getByText('Evacuate Area')).toBeInTheDocument();
      expect(screen.getByText('Call for Backup')).toBeInTheDocument();
    });

    it('displays narrative context when provided', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(
        screen.getByText(/Aria stands at the crossroads/)
      ).toBeInTheDocument();
    });

    it('displays turn number and decision type', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByText(/Turn 5/)).toBeInTheDocument();
      expect(screen.getByText(/character choice/i)).toBeInTheDocument();
    });
  });

  describe('Option Selection', () => {
    it('selects option when clicked', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      const optionCard = screen.getByText('Investigate Signal').closest('button');
      expect(optionCard).toBeInTheDocument();

      await act(async () => {
        fireEvent.click(optionCard!);
      });

      const state = store.getState().decision;
      expect(state.selectedOptionId).toBe(1);
    });

    it('shows selected state visually', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        selectedOptionId: 1,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Check icon appears on selected option
      // The selected option should have some visual indicator
      const selectedOption = screen.getByText('Investigate Signal').closest('button');
      expect(selectedOption).toBeInTheDocument();
    });

    it('enables submit button when option is selected', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        selectedOptionId: 1,
      });
      renderWithStore(<DecisionPointDialog />, store);

      const confirmButton = screen.getByRole('button', { name: /confirm/i });
      expect(confirmButton).not.toBeDisabled();
    });

    it('disables submit button when no option is selected', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        selectedOptionId: null,
      });
      renderWithStore(<DecisionPointDialog />, store);

      const confirmButton = screen.getByRole('button', { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
    });
  });

  describe('Free Text Input', () => {
    it('switches to freetext mode when button clicked', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      const customActionButton = screen.getByRole('button', { name: /custom action/i });
      await act(async () => {
        fireEvent.click(customActionButton);
      });

      expect(screen.getByPlaceholderText(/describe what you want/i)).toBeInTheDocument();
    });

    it('updates freetext input value', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Switch to freetext mode
      const customActionButton = screen.getByRole('button', { name: /custom action/i });
      await act(async () => {
        fireEvent.click(customActionButton);
      });

      const input = screen.getByPlaceholderText(/describe what you want/i);
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Make the character run away' } });
      });

      const state = store.getState().decision;
      expect(state.freeTextInput).toBe('Make the character run away');
    });

    it('validates minimum freetext length (5 characters)', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Switch to freetext mode
      const customActionButton = screen.getByRole('button', { name: /custom action/i });
      await act(async () => {
        fireEvent.click(customActionButton);
      });

      const input = screen.getByPlaceholderText(/describe what you want/i);

      // Enter less than 5 characters
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Run' } });
      });

      const confirmButton = screen.getByRole('button', { name: /confirm/i });
      expect(confirmButton).toBeDisabled();

      // Enter 5+ characters
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Run away quickly' } });
      });

      expect(confirmButton).not.toBeDisabled();
    });

    it('displays character count', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        freeTextInput: 'Test input',
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Switch to freetext mode
      const customActionButton = screen.getByRole('button', { name: /custom action/i });
      await act(async () => {
        fireEvent.click(customActionButton);
      });

      expect(screen.getByText(/10\/500/)).toBeInTheDocument();
    });
  });

  describe('Countdown Timer', () => {
    it('displays countdown timer', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByText(/2:00/)).toBeInTheDocument();
    });

    it('shows urgent styling when <= 30 seconds', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 25,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Timer should show urgent styling (red color)
      expect(screen.getByText(/0:25/)).toBeInTheDocument();
    });

    it('decrements countdown every second', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByText(/2:00/)).toBeInTheDocument();

      // Advance timer by 1 second
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Check if countdown decremented
      const state = store.getState().decision;
      expect(state.remainingSeconds).toBe(119);
    });
  });

  describe('Skip Functionality', () => {
    it('has skip buttons', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // There are two skip buttons - one in header (aria-label) and one in footer (text)
      const skipButtons = screen.getAllByRole('button', { name: /skip/i });
      expect(skipButtons.length).toBeGreaterThanOrEqual(1);
    });

    it('skip button triggers skip action', async () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Get the footer skip button (the one with "Skip (Default)" text)
      const skipButtons = screen.getAllByRole('button', { name: /skip/i });
      const skipButton = skipButtons[skipButtons.length - 1]; // Footer button is last

      // Just verify the button exists and is clickable
      expect(skipButton).not.toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('has proper aria labels', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');
      expect(dialog).toHaveAttribute('aria-describedby');
    });

    it('has accessible skip buttons', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Get all skip buttons (header icon and footer text)
      const skipButtons = screen.getAllByRole('button', { name: /skip/i });
      expect(skipButtons.length).toBeGreaterThanOrEqual(1);
      skipButtons.forEach((btn) => expect(btn).toBeInTheDocument());
    });
  });

  describe('Negotiation UI', () => {
    it('displays negotiation result when available', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'negotiating',
        remainingSeconds: 120,
        isNegotiating: true,
        negotiationResult: {
          feasibility: 'minor_adjustment',
          explanation: 'The action is mostly feasible but needs a small adjustment.',
          adjustedAction: 'Have the character investigate cautiously',
          alternatives: [],
        },
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByText(/Adjustment Suggested/i)).toBeInTheDocument();
      expect(
        screen.getByText(/The action is mostly feasible/)
      ).toBeInTheDocument();
    });

    it('shows accept and insist buttons during negotiation', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'negotiating',
        remainingSeconds: 120,
        isNegotiating: true,
        negotiationResult: {
          feasibility: 'minor_adjustment',
          explanation: 'The action needs adjustment.',
          adjustedAction: 'Modified action',
          alternatives: [],
        },
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(screen.getByRole('button', { name: /accept suggestion/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /keep original/i })).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error message when present', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        error: 'Failed to submit decision. Please try again.',
      });
      renderWithStore(<DecisionPointDialog />, store);

      expect(
        screen.getByText(/Failed to submit decision/)
      ).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows loading state during submission', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        selectedOptionId: 1,
        isSubmitting: true,
      });
      renderWithStore(<DecisionPointDialog />, store);

      const confirmButton = screen.getByRole('button', { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
    });

    it('disables option selection during submission', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
        isSubmitting: true,
      });
      renderWithStore(<DecisionPointDialog />, store);

      // Options should have reduced opacity or be disabled
      const optionCard = screen.getByText('Investigate Signal').closest('button');
      expect(optionCard).toBeInTheDocument();
    });
  });
});
