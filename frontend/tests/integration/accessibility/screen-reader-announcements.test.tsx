import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { vi } from 'vitest';
import CharacterSelection from '../../../src/components/CharacterSelection';

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
    t: (key: string, params?: any) => {
      if (key === 'characterSelection.counter' && params) {
        return `${params.count} characters selected`;
      }
      return key;
    },
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
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('Screen Reader Announcements', () => {
  it('should have aria-live="polite" region for dynamic updates', async () => {
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
  });

  it('should announce selection changes to screen readers', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).toHaveTextContent(/0.*selected/i);
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    await user.click(characterCard);
    
    await waitFor(() => {
      expect(liveRegion).toHaveTextContent(/1.*selected/i);
    });
  });

  it('should announce deselection to screen readers', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const liveRegion = screen.getByRole('status', { hidden: true });
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    await user.click(characterCard);
    await waitFor(() => {
      expect(liveRegion).toHaveTextContent(/1.*selected/i);
    });
    
    await user.click(characterCard);
    await waitFor(() => {
      expect(liveRegion).toHaveTextContent(/0.*selected/i);
    });
  });

  it('should announce validation errors in aria-live region', async () => {
    const user = userEvent.setup();
    
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    // Validation error should be visible by default (no characters selected)
    const errorRegion = screen.getByRole('alert');
    expect(errorRegion).toBeInTheDocument();
    expect(errorRegion).toHaveAttribute('aria-atomic', 'true');
  });

  it('should not use aria-live="assertive" for non-critical updates', async () => {
    const { container } = render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const assertiveRegions = container.querySelectorAll('[aria-live="assertive"]');
    
    // Selection counter should use polite, not assertive
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).not.toHaveAttribute('aria-live', 'assertive');
  });

  it('should maintain aria-pressed state across interactions', async () => {
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
    
    // Select multiple characters
    await user.click(characterCards[0]);
    await user.click(characterCards[1]);
    
    // Verify aria-pressed states
    expect(characterCards[0]).toHaveAttribute('aria-pressed', 'true');
    expect(characterCards[1]).toHaveAttribute('aria-pressed', 'true');
    expect(characterCards[2]).toHaveAttribute('aria-pressed', 'false');
  });

  it('should have descriptive aria-labels for all interactive elements', async () => {
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /select character/i })).toHaveLength(3);
    });
    
    const buttons = screen.getAllByRole('button');
    
    buttons.forEach(button => {
      const hasAriaLabel = button.hasAttribute('aria-label');
      const hasTextContent = button.textContent && button.textContent.trim().length > 0;
      
      // Each button must have either aria-label or visible text
      expect(hasAriaLabel || hasTextContent).toBe(true);
    });
  });
});
