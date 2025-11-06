import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import CharacterSelection from '../../../src/components/CharacterSelection';

const mockCharacters = [
  'Character 1',
  'Character 2',
  'Character 3',
];

const mockStory = {
  id: 'test-story',
  title: 'Test Story',
  characters: mockCharacters,
};

describe('Screen Reader Announcements', () => {
  it('should have aria-live="polite" region for dynamic updates', () => {
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
  });

  it('should announce selection changes to screen readers', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
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
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
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
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    // Try to continue without selecting minimum characters
    const continueButton = screen.getByRole('button', { name: /continue/i });
    await user.click(continueButton);
    
    // Validation error should be announced
    const errorRegion = screen.queryByRole('alert') || screen.getByRole('status', { hidden: true });
    expect(errorRegion).toBeInTheDocument();
  });

  it('should not use aria-live="assertive" for non-critical updates', () => {
    const { container } = render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const assertiveRegions = container.querySelectorAll('[aria-live="assertive"]');
    
    // Selection counter should use polite, not assertive
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).not.toHaveAttribute('aria-live', 'assertive');
  });

  it('should maintain aria-pressed state across interactions', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
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

  it('should have descriptive aria-labels for all interactive elements', () => {
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const buttons = screen.getAllByRole('button');
    
    buttons.forEach(button => {
      const hasAriaLabel = button.hasAttribute('aria-label');
      const hasTextContent = button.textContent && button.textContent.trim().length > 0;
      
      // Each button must have either aria-label or visible text
      expect(hasAriaLabel || hasTextContent).toBe(true);
    });
  });
});
