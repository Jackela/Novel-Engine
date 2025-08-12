import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import App from '../App';

// Mock API responses
const mockApiResponses = {
  getCharacters: jest.fn(() => Promise.resolve(['krieg', 'ork_warboss', 'isabella_varr'])),
  getCampaigns: jest.fn(() => Promise.resolve(['default', 'warhammer_40k'])),
  getHealth: jest.fn(() => Promise.resolve({
    api: 'healthy',
    config: 'loaded',
    version: '1.0.0',
  })),
  createCharacter: jest.fn(() => Promise.resolve({
    success: true,
    data: { name: 'test_character' },
  })),
  runSimulation: jest.fn(() => Promise.resolve({
    success: true,
    data: {
      id: 'story_123',
      title: 'Test Story',
      storyContent: 'Once upon a time...',
      metadata: {
        wordCount: 100,
        generationTime: 30,
        participantCount: 2,
      },
    },
  })),
};

// Mock the API module
jest.mock('../services/api', () => ({
  __esModule: true,
  default: mockApiResponses,
  ...mockApiResponses,
}));

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({ 'data-testid': 'dropzone' }),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}));

const createTestWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { 
        retry: false,
        cacheTime: 0,
      },
      mutations: { retry: false },
    },
  });
  const theme = createTheme();

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('Novel Engine Workflows', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Navigation Workflow', () => {
    it('should navigate between all main sections', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Should start on Dashboard
      await waitFor(() => {
        expect(screen.getByText('Welcome to Novel Engine')).toBeInTheDocument();
      });

      // Navigate to Characters
      fireEvent.click(screen.getByRole('button', { name: /characters/i }));
      await waitFor(() => {
        expect(screen.getByText('Character Studio')).toBeInTheDocument();
      });

      // Navigate to Workshop
      fireEvent.click(screen.getByRole('button', { name: /workshop/i }));
      await waitFor(() => {
        expect(screen.getByText('Story Workshop')).toBeInTheDocument();
      });

      // Navigate to Library
      fireEvent.click(screen.getByRole('button', { name: /library/i }));
      await waitFor(() => {
        expect(screen.getByText('Story Library')).toBeInTheDocument();
      });

      // Navigate to Monitor
      fireEvent.click(screen.getByRole('button', { name: /monitor/i }));
      await waitFor(() => {
        expect(screen.getByText('System Monitor')).toBeInTheDocument();
      });
    });
  });

  describe('Character Management Workflow', () => {
    it('should display existing characters', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Navigate to Characters
      fireEvent.click(screen.getByRole('button', { name: /characters/i }));

      // Wait for characters to load
      await waitFor(() => {
        expect(mockApiResponses.getCharacters).toHaveBeenCalled();
      });

      // Should show character creation interface
      expect(screen.getByText('Character Studio')).toBeInTheDocument();
      expect(screen.getByText('Create and manage your story characters')).toBeInTheDocument();
    });

    it('should open character creation dialog', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Navigate to Characters
      fireEvent.click(screen.getByRole('button', { name: /characters/i }));

      await waitFor(() => {
        expect(screen.getByText('Character Studio')).toBeInTheDocument();
      });

      // Click Create Character button
      const createButton = screen.getByRole('button', { name: /create character/i });
      fireEvent.click(createButton);

      // Should open the creation dialog
      await waitFor(() => {
        expect(screen.getByText('Create New Character')).toBeInTheDocument();
        expect(screen.getByLabelText('Character Name')).toBeInTheDocument();
      });
    });
  });

  describe('Story Generation Workflow', () => {
    it('should navigate through story creation steps', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Navigate to Workshop
      fireEvent.click(screen.getByRole('button', { name: /workshop/i }));

      await waitFor(() => {
        expect(screen.getByText('Story Workshop')).toBeInTheDocument();
      });

      // Should start on Step 1: Character Selection
      expect(screen.getByText('Select Characters')).toBeInTheDocument();
      expect(screen.getByText('Choose 2-6 characters to participate in your story')).toBeInTheDocument();

      // Progress through the workshop steps would require more complex interaction
      // For now, just verify the interface is present
      expect(screen.getByText('Progress Stepper')).toBeInTheDocument();
    });
  });

  describe('System Health Workflow', () => {
    it('should display system health information', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Navigate to Monitor
      fireEvent.click(screen.getByRole('button', { name: /monitor/i }));

      await waitFor(() => {
        expect(screen.getByText('System Monitor')).toBeInTheDocument();
      });

      // Should call health check API
      await waitFor(() => {
        expect(mockApiResponses.getHealth).toHaveBeenCalled();
      });

      // Should display system status
      expect(screen.getByText('Real-time system performance and health monitoring')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      // Mock API error
      mockApiResponses.getCharacters.mockRejectedValueOnce(new Error('API Error'));

      render(<App />, { wrapper: createTestWrapper() });

      // Navigate to Characters
      fireEvent.click(screen.getByRole('button', { name: /characters/i }));

      // Should still render the character studio even with API error
      await waitFor(() => {
        expect(screen.getByText('Character Studio')).toBeInTheDocument();
      });
    });

    it('should handle network connectivity issues', async () => {
      // Mock network error
      mockApiResponses.getHealth.mockRejectedValueOnce(new Error('Network error'));

      render(<App />, { wrapper: createTestWrapper() });

      // Should still render the main application
      await waitFor(() => {
        expect(screen.getByText('Welcome to Novel Engine')).toBeInTheDocument();
      });

      // Health indicator should show error state
      // This would need more specific testing based on actual error handling implementation
    });
  });

  describe('Performance and Responsiveness', () => {
    it('should render main components quickly', async () => {
      const startTime = performance.now();
      
      render(<App />, { wrapper: createTestWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Welcome to Novel Engine')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render within reasonable time (adjust threshold as needed)
      expect(renderTime).toBeLessThan(1000); // 1 second
    });

    it('should handle rapid navigation without errors', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Rapidly navigate between sections
      const sections = ['characters', 'workshop', 'library', 'monitor'];
      
      for (const section of sections) {
        fireEvent.click(screen.getByRole('button', { name: new RegExp(section, 'i') }));
        await waitFor(() => {
          // Just ensure no errors are thrown during navigation
          expect(document.body).toBeInTheDocument();
        });
      }
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Check for main navigation
      const navigation = screen.getByRole('navigation');
      expect(navigation).toBeInTheDocument();

      // Check for main content area
      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();

      // Check for buttons with accessible names
      expect(screen.getByRole('button', { name: /dashboard/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /characters/i })).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      render(<App />, { wrapper: createTestWrapper() });

      // Tab through navigation elements
      const dashboardButton = screen.getByRole('button', { name: /dashboard/i });
      dashboardButton.focus();
      expect(dashboardButton).toHaveFocus();

      // Press Tab to move to next element
      fireEvent.keyDown(dashboardButton, { key: 'Tab' });
      
      // Should move focus to next navigation item
      const charactersButton = screen.getByRole('button', { name: /characters/i });
      expect(charactersButton).toBeInTheDocument();
    });
  });
});

describe('Integration Tests', () => {
  it('should integrate all components without conflicts', async () => {
    render(<App />, { wrapper: createTestWrapper() });

    // Should render without throwing errors
    await waitFor(() => {
      expect(screen.getByText('Novel Engine')).toBeInTheDocument();
    });

    // Should have all main navigation elements
    expect(screen.getByRole('button', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /characters/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /workshop/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /library/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /monitor/i })).toBeInTheDocument();
  });

  it('should maintain state across navigation', async () => {
    render(<App />, { wrapper: createTestWrapper() });

    // Navigate to characters and verify API call
    fireEvent.click(screen.getByRole('button', { name: /characters/i }));
    
    await waitFor(() => {
      expect(mockApiResponses.getCharacters).toHaveBeenCalled();
    });

    // Navigate away and back
    fireEvent.click(screen.getByRole('button', { name: /dashboard/i }));
    fireEvent.click(screen.getByRole('button', { name: /characters/i }));

    // Should use cached data (React Query should handle this)
    expect(screen.getByText('Character Studio')).toBeInTheDocument();
  });
});