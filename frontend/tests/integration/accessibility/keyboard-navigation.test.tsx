import { render, screen, within } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import CharacterSelection from '../../../src/components/CharacterSelection';

expect.extend(toHaveNoViolations);

const mockCharacters = [
  { 
    id: '1', 
    name: 'Character 1', 
    role: 'protagonist',
    description: 'Test character 1'
  },
  { 
    id: '2', 
    name: 'Character 2', 
    role: 'antagonist',
    description: 'Test character 2'
  },
  { 
    id: '3', 
    name: 'Character 3', 
    role: 'supporting',
    description: 'Test character 3'
  },
];

const mockStory = {
  id: 'test-story',
  title: 'Test Story',
  characters: mockCharacters,
};

describe('Keyboard Navigation Integration', () => {
  it('should not have accessibility violations in CharacterSelection', async () => {
    const { container } = render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should allow full keyboard navigation through character cards', async () => {
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
    
    expect(characterCards).toHaveLength(3);
    
    characterCards[0].focus();
    expect(characterCards[0]).toHaveFocus();
    
    await user.tab();
    expect(characterCards[1]).toHaveFocus();
    
    await user.tab();
    expect(characterCards[2]).toHaveFocus();
  });

  it('should allow character selection with Enter key', async () => {
    const user = userEvent.setup();
    const handleSelection = vi.fn();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={handleSelection}
        />
      </BrowserRouter>
    );
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    characterCard.focus();
    await user.keyboard('{Enter}');
    
    expect(characterCard).toHaveAttribute('aria-pressed', 'true');
  });

  it('should allow character selection with Space key', async () => {
    const user = userEvent.setup();
    const handleSelection = vi.fn();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={handleSelection}
        />
      </BrowserRouter>
    );
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    characterCard.focus();
    await user.keyboard(' ');
    
    expect(characterCard).toHaveAttribute('aria-pressed', 'true');
  });

  it('should show visible focus indicators on character cards', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    await user.tab();
    
    const styles = window.getComputedStyle(characterCard);
    expect(styles.outline).not.toBe('none');
    expect(styles.outline).not.toBe('');
  });

  it('should navigate with arrow keys within character grid', async () => {
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
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const characterCard = screen.getAllByRole('button', { 
      name: /select character/i 
    })[0];
    
    characterCard.focus();
    await user.keyboard('{Enter}');
    
    const liveRegion = screen.getByRole('status', { hidden: true });
    expect(liveRegion).toHaveTextContent(/1.*selected/i);
  });

  it('should trap focus in modal when validation fails', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const continueButton = screen.getByRole('button', { name: /continue/i });
    await user.click(continueButton);
    
    const modal = screen.getByRole('dialog');
    expect(modal).toBeInTheDocument();
    
    const firstFocusable = within(modal).getAllByRole('button')[0];
    expect(firstFocusable).toHaveFocus();
  });

  it('should close modal with Escape key', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <CharacterSelection 
          story={mockStory}
          onCharactersSelected={() => {}}
        />
      </BrowserRouter>
    );
    
    const continueButton = screen.getByRole('button', { name: /continue/i });
    await user.click(continueButton);
    
    const modal = screen.getByRole('dialog');
    expect(modal).toBeInTheDocument();
    
    await user.keyboard('{Escape}');
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
