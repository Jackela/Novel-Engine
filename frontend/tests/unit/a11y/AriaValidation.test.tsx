import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
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

describe('ARIA Attribute Validation', () => {
  it('should have no accessibility violations in CharacterSelection', async () => {
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

  it('should have proper aria-label on character cards', async () => {
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      const characterCard = screen.getAllByRole('button', { 
        name: /select character/i 
      })[0];
      
      expect(characterCard).toHaveAttribute('aria-label', expect.stringContaining('Select character'));
    });
  });

  it('should have aria-pressed attribute on character cards', async () => {
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      const characterCards = screen.getAllByRole('button', { 
        name: /select character/i 
      });
      
      characterCards.forEach(card => {
        expect(card).toHaveAttribute('aria-pressed');
      });
    });
  });

  it('should update aria-pressed when character is selected', async () => {
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    // Wait for initial render with aria-pressed="false"
    const characterCard = await screen.findByRole('button', { 
      name: /select character character_1/i,
      pressed: false
    });
    
    expect(characterCard).toHaveAttribute('aria-pressed', 'false');
    
    await act(async () => {
      characterCard.click();
    });

    await waitFor(() => {
      expect(characterCard).toHaveAttribute('aria-pressed', 'true');
    });
  });

  it('should have aria-live region for selection counter', async () => {
    render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      // Check for selection counter with aria-live
      const selectionCounter = screen.getByTestId('selection-counter');
      expect(selectionCounter).toHaveAttribute('aria-live', 'polite');
    });
  });

  it('should have semantic HTML structure', async () => {
    const { container } = render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      const buttons = screen.getAllByRole('button', { name: /select character/i });
      expect(buttons.length).toBeGreaterThan(0);
    });
    
    // Check for proper heading structure
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
    expect(headings.length).toBeGreaterThan(0);
    
    // Check for proper button elements (role="button" is acceptable alternative)
    const buttons = container.querySelectorAll('button, [role="button"]');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have proper ARIA attributes on div role="button" elements', async () => {
    const { container } = render(<CharacterSelection />, {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      const buttons = screen.getAllByRole('button', { name: /select character/i });
      expect(buttons.length).toBeGreaterThan(0);
    });
    
    const divButtons = container.querySelectorAll('div[role="button"]');
    
    divButtons.forEach(button => {
      // Each div with role="button" must have tabIndex
      expect(button.hasAttribute('tabIndex') || button.hasAttribute('tabindex')).toBe(true);
      
      // Must have either aria-label or text content
      const hasAriaLabel = button.hasAttribute('aria-label');
      const hasTextContent = button.textContent && button.textContent.trim().length > 0;
      
      expect(hasAriaLabel || hasTextContent).toBe(true);
    });
  });
});
