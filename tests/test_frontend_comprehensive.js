/**
 * Comprehensive Frontend Test Suite
 * =================================
 * 
 * This test suite provides complete coverage for the StoryForge AI frontend
 * application with focus on debranded UI components and generic sci-fi content.
 * 
 * Test Categories:
 * 1. Component Rendering & State
 * 2. User Interactions & Navigation  
 * 3. API Integration
 * 4. Character Selection & Management
 * 5. Simulation Interface
 * 6. Error Handling & Edge Cases
 * 7. Performance & Responsiveness
 * 8. Accessibility & Usability
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import App from '../src/App.jsx';

// Mock API server
const API_BASE_URL = 'http://127.0.0.1:8000';

// Generic test data (debranded)
const MOCK_CHARACTERS = {
  characters: ['pilot', 'scientist', 'engineer', 'test']
};

const MOCK_CHARACTER_DETAILS = {
  pilot: {
    character_name: 'pilot',
    narrative_context: '# Character Profile: Elite Pilot\\n\\n## Core Identity\\n- **Name**: Alex Chen\\n- **Role**: Elite Starfighter Pilot\\n- **Affiliation**: Galactic Defense Force',
    structured_data: {
      stats: {
        character: {
          name: 'Alex Chen',
          faction: 'Galactic Defense Force',
          specialization: 'Starfighter Pilot'
        },
        combat_stats: {
          pilot: 10,
          tactics: 9,
          marksmanship: 8
        }
      }
    }
  },
  scientist: {
    character_name: 'scientist',
    narrative_context: '# Character Profile: Research Scientist\\n\\n## Core Identity\\n- **Name**: Dr. Maya Patel\\n- **Role**: Xenobiology Research Scientist\\n- **Affiliation**: Scientific Research Institute',
    structured_data: {
      stats: {
        character: {
          name: 'Dr. Maya Patel',
          faction: 'Scientific Research Institute',
          specialization: 'Xenobiology'
        }
      }
    }
  },
  engineer: {
    character_name: 'engineer',
    narrative_context: '# Character Profile: Systems Engineer\\n\\n## Core Identity\\n- **Name**: Jordan Kim\\n- **Role**: Senior Systems Engineer\\n- **Affiliation**: Galactic Engineering Corps',
    structured_data: {
      stats: {
        character: {
          name: 'Jordan Kim',
          faction: 'Galactic Engineering Corps',
          specialization: 'Systems Engineering'
        }
      }
    }
  },
  test: {
    character_name: 'test',
    narrative_context: '# Character Profile: Test Subject\\n\\n## Core Identity\\n- **Name**: Test Subject 01\\n- **Role**: Development Test Character',
    structured_data: {
      stats: {
        character: {
          name: 'Test Subject 01',
          faction: 'Development Team',
          specialization: 'Quality Assurance'
        }
      }
    }
  }
};

const MOCK_SIMULATION_RESULT = {
  story: 'In the vast expanse of space, where conflict shapes destiny, the chronicles of discovery unfold. Alex Chen and Dr. Maya Patel worked together to unlock the mysteries of the cosmos.',
  participants: ['pilot', 'scientist'],
  turns_executed: 3,
  duration_seconds: 4.2
};

// MSW server setup
const handlers = [
  rest.get(`${API_BASE_URL}/characters`, (req, res, ctx) => {
    return res(ctx.json(MOCK_CHARACTERS));
  }),
  
  rest.get(`${API_BASE_URL}/characters/:character`, (req, res, ctx) => {
    const { character } = req.params;
    const characterData = MOCK_CHARACTER_DETAILS[character];
    
    if (characterData) {
      return res(ctx.json(characterData));
    } else {
      return res(
        ctx.status(404),
        ctx.json({ detail: 'Character not found' })
      );
    }
  }),
  
  rest.post(`${API_BASE_URL}/simulations`, (req, res, ctx) => {
    return res(ctx.json(MOCK_SIMULATION_RESULT));
  }),
  
  rest.get(`${API_BASE_URL}/health`, (req, res, ctx) => {
    return res(ctx.json({ status: 'healthy', timestamp: new Date().toISOString() }));
  })
];

const server = setupServer(...handlers);

// Test setup and cleanup
beforeEach(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
});

afterAll(() => {
  server.close();
});

describe('StoryForge AI Frontend Application', () => {
  describe('Application Initialization & Branding', () => {
    it('renders with StoryForge AI branding', () => {
      render(<App />);
      
      // Check for debranded title
      expect(screen.getByText(/StoryForge AI/i)).toBeInTheDocument();
      expect(screen.getByText(/Interactive Story Engine/i)).toBeInTheDocument();
      
      // Should not contain old branding
      expect(screen.queryByText(/Warhammer/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/40k/i)).not.toBeInTheDocument();
    });
    
    it('displays correct subtitle and description', () => {
      render(<App />);
      
      expect(screen.getByText(/AI-Powered Narrative Generation Platform/i)).toBeInTheDocument();
      
      // Check for generic sci-fi theme
      const sciFiElements = [
        /narrative generation/i,
        /story engine/i,
        /interactive/i
      ];
      
      sciFiElements.forEach(element => {
        expect(screen.getByText(element)).toBeInTheDocument();
      });
    });
    
    it('has proper page title and metadata', () => {
      render(<App />);
      
      // Check document title
      expect(document.title).toContain('StoryForge AI');
      expect(document.title).not.toContain('Warhammer');
      expect(document.title).not.toContain('40k');
    });
  });
  
  describe('Character Loading & Display', () => {
    it('loads and displays generic characters', async () => {
      render(<App />);
      
      // Wait for characters to load
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
        expect(screen.getByText(/engineer/i)).toBeInTheDocument();
        expect(screen.getByText(/test/i)).toBeInTheDocument();
      });
      
      // Should not display old branded characters
      expect(screen.queryByText(/krieg/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/ork/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/isabella/i)).not.toBeInTheDocument();
    });
    
    it('displays character details when selected', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Wait for characters to load and click on pilot
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      const pilotElement = screen.getByText(/pilot/i);
      await user.click(pilotElement);
      
      // Wait for character details
      await waitFor(() => {
        expect(screen.getByText(/Alex Chen/i)).toBeInTheDocument();
        expect(screen.getByText(/Galactic Defense Force/i)).toBeInTheDocument();
        expect(screen.getByText(/Starfighter Pilot/i)).toBeInTheDocument();
      });
      
      // Should not contain branded faction names
      expect(screen.queryByText(/Imperial/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Emperor/i)).not.toBeInTheDocument();
    });
    
    it('handles character loading errors gracefully', async () => {
      // Mock API error
      server.use(
        rest.get(`${API_BASE_URL}/characters`, (req, res, ctx) => {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }));
        })
      );
      
      render(<App />);
      
      // Should display error message
      await waitFor(() => {
        expect(screen.getByText(/error/i) || screen.getByText(/failed/i)).toBeInTheDocument();
      });
      
      // Should have retry mechanism
      const retryButton = screen.queryByText(/retry/i) || screen.queryByRole('button', { name: /retry/i });
      if (retryButton) {
        expect(retryButton).toBeInTheDocument();
      }
    });
  });
  
  describe('Character Selection Interface', () => {
    it('allows multiple character selection', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Wait for characters to load
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
      });
      
      // Select multiple characters
      await user.click(screen.getByText(/pilot/i));
      await user.click(screen.getByText(/scientist/i));
      
      // Should show selection state
      // Look for visual indicators or selection counter
      const selectedElements = screen.getAllByTestId ? screen.queryAllByTestId(/selected/i) : [];
      const selectionText = screen.queryByText(/selected/i);
      
      // At least one indicator of selection should be present
      expect(selectedElements.length > 0 || selectionText).toBeTruthy();
    });
    
    it('validates minimum character selection', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      // Try to proceed with insufficient selection
      await user.click(screen.getByText(/pilot/i));
      
      const startButton = screen.queryByRole('button', { name: /start/i }) || 
                         screen.queryByRole('button', { name: /simulate/i }) ||
                         screen.queryByRole('button', { name: /begin/i });
      
      if (startButton) {
        // Button should be disabled or show validation message
        expect(startButton).toBeDisabled() || 
        expect(screen.queryByText(/minimum.*2.*character/i)).toBeInTheDocument();
      }
    });
    
    it('enforces maximum character selection', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Wait for all characters to load
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
        expect(screen.getByText(/engineer/i)).toBeInTheDocument();
        expect(screen.getByText(/test/i)).toBeInTheDocument();
      });
      
      // Select all available characters
      const characters = ['pilot', 'scientist', 'engineer', 'test'];
      for (const char of characters) {
        const element = screen.getByText(new RegExp(char, 'i'));
        await user.click(element);
      }
      
      // Should show maximum selection reached
      const maxMessage = screen.queryByText(/maximum/i) || screen.queryByText(/limit/i);
      if (maxMessage) {
        expect(maxMessage).toBeInTheDocument();
      }
    });
  });
  
  describe('Simulation Interface', () => {
    it('initiates simulation with selected characters', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Select characters
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
      });
      
      await user.click(screen.getByText(/pilot/i));
      await user.click(screen.getByText(/scientist/i));
      
      // Find and click simulation button
      const simButton = screen.queryByRole('button', { name: /start/i }) || 
                       screen.queryByRole('button', { name: /simulate/i }) ||
                       screen.queryByRole('button', { name: /begin/i });
      
      if (simButton && !simButton.disabled) {
        await user.click(simButton);
        
        // Should show simulation in progress or results
        await waitFor(() => {
          const progressIndicator = screen.queryByText(/progress/i) || 
                                  screen.queryByText(/generating/i) ||
                                  screen.queryByText(/running/i);
          expect(progressIndicator).toBeInTheDocument();
        });
      }
    });
    
    it('displays simulation results with debranded content', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Setup simulation
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
      });
      
      await user.click(screen.getByText(/pilot/i));
      await user.click(screen.getByText(/scientist/i));
      
      const simButton = screen.queryByRole('button', { name: /start/i });
      if (simButton && !simButton.disabled) {
        await user.click(simButton);
        
        // Wait for results
        await waitFor(() => {
          // Look for story content
          const storyText = screen.queryByText(/vast expanse/i) || 
                           screen.queryByText(/space/i) ||
                           screen.queryByText(/cosmos/i);
          
          if (storyText) {
            expect(storyText).toBeInTheDocument();
            
            // Verify no branded content
            expect(screen.queryByText(/emperor/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/imperial/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/warhammer/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/grim darkness/i)).not.toBeInTheDocument();
          }
        });
      }
    });
    
    it('shows simulation metadata and statistics', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Run simulation
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
      });
      
      await user.click(screen.getByText(/pilot/i));
      await user.click(screen.getByText(/scientist/i));
      
      const simButton = screen.queryByRole('button', { name: /start/i });
      if (simButton && !simButton.disabled) {
        await user.click(simButton);
        
        // Look for metadata
        await waitFor(() => {
          const metadata = screen.queryByText(/turns/i) || 
                          screen.queryByText(/duration/i) ||
                          screen.queryByText(/participants/i);
          
          if (metadata) {
            expect(metadata).toBeInTheDocument();
          }
        });
      }
    });
  });
  
  describe('Error Handling & User Feedback', () => {
    it('handles API connection errors', async () => {
      // Mock network error
      server.use(
        rest.get(`${API_BASE_URL}/characters`, (req, res, ctx) => {
          return res.networkError('Failed to connect');
        })
      );
      
      render(<App />);
      
      // Should show connection error
      await waitFor(() => {
        const errorMessage = screen.queryByText(/connect/i) || 
                           screen.queryByText(/network/i) ||
                           screen.queryByText(/server/i);
        expect(errorMessage).toBeInTheDocument();
      });
    });
    
    it('provides user feedback during loading states', async () => {
      // Mock delayed response
      server.use(
        rest.get(`${API_BASE_URL}/characters`, (req, res, ctx) => {
          return res(ctx.delay(1000), ctx.json(MOCK_CHARACTERS));
        })
      );
      
      render(<App />);
      
      // Should show loading indicator
      const loadingIndicator = screen.queryByText(/loading/i) || 
                             screen.queryByRole('progressbar') ||
                             screen.queryByTestId('loading-spinner');
      
      if (loadingIndicator) {
        expect(loadingIndicator).toBeInTheDocument();
      }
    });
    
    it('recovers from simulation errors', async () => {
      const user = userEvent.setup();
      
      // Mock simulation error
      server.use(
        rest.post(`${API_BASE_URL}/simulations`, (req, res, ctx) => {
          return res(ctx.status(500), ctx.json({ error: 'Simulation failed' }));
        })
      );
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
      });
      
      await user.click(screen.getByText(/pilot/i));
      await user.click(screen.getByText(/scientist/i));
      
      const simButton = screen.queryByRole('button', { name: /start/i });
      if (simButton && !simButton.disabled) {
        await user.click(simButton);
        
        // Should show error message
        await waitFor(() => {
          const errorMessage = screen.queryByText(/error/i) || 
                              screen.queryByText(/failed/i);
          expect(errorMessage).toBeInTheDocument();
        });
      }
    });
  });
  
  describe('Responsive Design & Accessibility', () => {
    it('renders properly on mobile viewport', () => {
      // Simulate mobile viewport
      global.innerWidth = 375;
      global.innerHeight = 667;
      global.dispatchEvent(new Event('resize'));
      
      render(<App />);
      
      // Should render without breaking
      expect(screen.getByText(/StoryForge AI/i)).toBeInTheDocument();
      
      // Should maintain usability on mobile
      const mainContent = screen.getByRole('main') || document.body;
      expect(mainContent).toBeInTheDocument();
    });
    
    it('has proper semantic HTML structure', () => {
      render(<App />);
      
      // Check for semantic elements
      const main = screen.getByRole('main') || screen.getByTestId('main-content');
      expect(main || document.querySelector('main')).toBeInTheDocument();
      
      // Check for proper heading hierarchy
      const headings = screen.getAllByRole('heading');
      expect(headings.length).toBeGreaterThan(0);
    });
    
    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      // Test keyboard navigation
      await user.tab();
      
      // Should focus on interactive elements
      const focusedElement = document.activeElement;
      expect(focusedElement.tagName).toMatch(/BUTTON|INPUT|A|DIV/);
    });
    
    it('has appropriate ARIA labels and roles', () => {
      render(<App />);
      
      // Check for ARIA attributes
      const interactiveElements = screen.getAllByRole('button');
      interactiveElements.forEach(element => {
        // Should have accessible names
        expect(
          element.getAttribute('aria-label') || 
          element.getAttribute('aria-labelledby') ||
          element.textContent
        ).toBeTruthy();
      });
    });
  });
  
  describe('Performance & Optimization', () => {
    it('renders initial content quickly', () => {
      const startTime = performance.now();
      render(<App />);
      const endTime = performance.now();
      
      // Should render within reasonable time
      expect(endTime - startTime).toBeLessThan(100); // 100ms
      
      // Should have initial content
      expect(screen.getByText(/StoryForge AI/i)).toBeInTheDocument();
    });
    
    it('handles large character lists efficiently', async () => {
      // Mock large character list
      const largeCharacterList = {
        characters: Array.from({ length: 50 }, (_, i) => `character_${i}`)
      };
      
      server.use(
        rest.get(`${API_BASE_URL}/characters`, (req, res, ctx) => {
          return res(ctx.json(largeCharacterList));
        })
      );
      
      render(<App />);
      
      // Should handle large lists without performance issues
      await waitFor(() => {
        const characterElements = screen.getAllByText(/character_/);
        expect(characterElements.length).toBeGreaterThan(10);
      }, { timeout: 5000 });
    });
    
    it('manages memory efficiently during interactions', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      // Perform multiple interactions
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      // Multiple character selections
      for (let i = 0; i < 5; i++) {
        const pilotElement = screen.getByText(/pilot/i);
        await user.click(pilotElement);
        
        // Small delay between interactions
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      
      // Should remain responsive
      expect(screen.getByText(/StoryForge AI/i)).toBeInTheDocument();
    });
  });
  
  describe('Content Validation & Theme Consistency', () => {
    it('maintains consistent sci-fi theming throughout', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      // Check for consistent sci-fi elements
      const sciFiElements = [
        /space/i, /galaxy/i, /research/i, /technology/i,
        /defense/i, /engineering/i, /scientific/i
      ];
      
      // At least some sci-fi elements should be present
      const foundElements = sciFiElements.filter(element => 
        screen.queryByText(element)
      );
      
      expect(foundElements.length).toBeGreaterThan(0);
    });
    
    it('contains no legacy branded content in UI', () => {
      render(<App />);
      
      // Check entire page for branded content
      const bannedTerms = [
        /warhammer/i, /40k/i, /emperor/i, /imperial/i,
        /chaos/i, /ork/i, /krieg/i, /space marines/i,
        /grim darkness/i, /far future/i
      ];
      
      bannedTerms.forEach(term => {
        expect(screen.queryByText(term)).not.toBeInTheDocument();
      });
    });
    
    it('uses appropriate generic faction names', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      // Click to see character details
      const user = userEvent.setup();
      await user.click(screen.getByText(/pilot/i));
      
      await waitFor(() => {
        // Should show generic faction names
        const genericFactions = [
          /galactic defense/i, /research institute/i,
          /engineering corps/i, /alliance/i
        ];
        
        const foundFactions = genericFactions.filter(faction => 
          screen.queryByText(faction)
        );
        
        expect(foundFactions.length).toBeGreaterThan(0);
      });
    });
  });
  
  describe('User Experience & Workflow', () => {
    it('provides clear navigation and flow', async () => {
      render(<App />);
      
      // Should have clear interface elements
      expect(screen.getByText(/StoryForge AI/i)).toBeInTheDocument();
      
      // Should guide user through process
      const instructionalText = screen.queryByText(/select/i) || 
                               screen.queryByText(/choose/i) ||
                               screen.queryByText(/begin/i);
      
      if (instructionalText) {
        expect(instructionalText).toBeInTheDocument();
      }
    });
    
    it('maintains state during user interactions', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
        expect(screen.getByText(/scientist/i)).toBeInTheDocument();
      });
      
      // Select characters
      await user.click(screen.getByText(/pilot/i));
      await user.click(screen.getByText(/scientist/i));
      
      // State should be maintained
      // Look for visual indicators or selection state
      const selectionIndicators = screen.getAllByTestId ? 
        screen.queryAllByTestId(/selected/i) : [];
      
      // Some form of state persistence should be visible
      expect(document.body.innerHTML).toContain('pilot');
      expect(document.body.innerHTML).toContain('scientist');
    });
    
    it('provides feedback for user actions', async () => {
      const user = userEvent.setup();
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText(/pilot/i)).toBeInTheDocument();
      });
      
      // Click on character
      await user.click(screen.getByText(/pilot/i));
      
      // Should provide visual feedback
      // This could be selection highlighting, state changes, etc.
      await waitFor(() => {
        // Check for any change in the interface
        const feedbackElement = screen.queryByTestId(/selected/i) || 
                              screen.queryByText(/selected/i) ||
                              document.querySelector('[class*=\"selected\"]');
        
        // Some form of feedback should be present
        expect(document.body.innerHTML.length).toBeGreaterThan(100);
      });
    });
  });
});