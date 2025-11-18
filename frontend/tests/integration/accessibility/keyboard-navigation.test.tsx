import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { vi } from 'vitest';
import CharacterSelection from '../../../src/components/CharacterSelection';

expect.extend(toHaveNoViolations);

const mockCharacters = [
  'character_1',
  'character_2',
  'character_3',
];

// Mock the queries module
vi.mock('../../../src/services/queries', () => ({
  useCharactersQuery: () => ({
    data: mockCharacters,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useStoryQuery: () => ({
    data: {
      id: 'test-story',
      name: 'Test Story',
      selectionConstraints: {
        minSelection: 1,
        maxSelection: 3,
      },
    },
    isLoading: false,
    error: null,
  }),
}));

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: vi.fn(),
    },
  }),
}));

// Create a test wrapper with all required providers
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('Keyboard Navigation Integration', () => {
  it('should not have accessibility violations in CharacterSelection', async () => {
    const { container } = render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    // Wait for characters to load
    await waitFor(() => {
      const buttons = screen.getAllByRole('button', { name: /select character/i });
      expect(buttons.length).toBeGreaterThan(0);
    });
    
    let results: Awaited<ReturnType<typeof axe>>;
    await act(async () => {
      results = await axe(container);
    });
    expect(results).toHaveNoViolations();
  });

  it('should allow full keyboard navigation through character cards', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCards = screen.getAllByRole('button', { 
      name: /select character/i 
    });
    
    // Focus first card
    characterCards[0].focus();
    expect(characterCards[0]).toHaveFocus();
    
    // Arrow key navigation
    await user.keyboard('{ArrowRight}');
    expect(characterCards[1]).toHaveFocus();
    
    await user.keyboard('{ArrowRight}');
    expect(characterCards[2]).toHaveFocus();
  });

  it('should allow character selection with Enter key', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    characterCard.focus();
    await user.keyboard('{Enter}');
    
    expect(characterCard).toHaveAttribute('aria-pressed', 'true');
  });

  it('should allow character selection with Space key', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    characterCard.focus();
    await user.keyboard(' ');
    
    expect(characterCard).toHaveAttribute('aria-pressed', 'true');
  });

  it('should show visible focus indicators on character cards', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCards = screen.getAllByRole('button', { 
      name: /select character/i 
    });
    
    // Tab to first character card
    await user.tab();
    
    // One of the character cards should have focus
    const focusedCard = characterCards.find(card => card === document.activeElement);
    expect(focusedCard).toBeDefined();
    expect(focusedCard).toHaveFocus();
  });

  it('should navigate with arrow keys within character grid', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCards = screen.getAllByRole('button', { 
      name: /select character/i 
    });
    
    characterCards[0].focus();
    expect(characterCards[0]).toHaveFocus();
    
    await user.keyboard('{ArrowRight}');
    expect(characterCards[1]).toHaveFocus();
    
    await user.keyboard('{ArrowRight}');
    expect(characterCards[2]).toHaveFocus();
    
    await user.keyboard('{ArrowLeft}');
    expect(characterCards[1]).toHaveFocus();
  });

  it('should announce selection count to screen readers', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    await user.click(characterCard);
    
    // Check that selection state is announced via aria-pressed
    expect(characterCard).toHaveAttribute('aria-pressed', 'true');
    
    // Verify selection counter is updated
    const confirmButton = screen.getByTestId('confirm-selection-button');
    expect(confirmButton).toHaveAttribute('aria-label', expect.stringMatching(/1.*character/i));
  });

  it('should show validation error when attempting to confirm without minimum characters', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    // Confirm button should be disabled when no characters selected
    const confirmButton = screen.getByTestId('confirm-selection-button');
    expect(confirmButton).toBeDisabled();
    
    // Validation error should be visible
    const errorMessage = screen.getByRole('alert');
    expect(errorMessage).toBeInTheDocument();
  });

  it('should enable confirm button when minimum characters selected', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const characterCards = screen.getAllByRole('button', { 
      name: /select character/i 
    });
    
    // Select minimum number of characters (min is 2)
    await user.click(characterCards[0]);
    await user.click(characterCards[1]);
    
    // Confirm button should now be enabled
    const confirmButton = screen.getByTestId('confirm-selection-button');
    
    await waitFor(() => {
      expect(confirmButton).not.toBeDisabled();
    });
  });
});
