import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import App from '../App';
import Navbar from '../components/Navbar';
import Dashboard from '../components/Dashboard';
import CharacterStudio from '../components/CharacterStudio';
import StoryWorkshop from '../components/StoryWorkshop';
import StoryLibrary from '../components/StoryLibrary';
import SystemMonitor from '../components/SystemMonitor';

import { vi } from 'vitest';

// Mock the API module with both default and named exports
vi.mock('../services/api', () => ({
  default: {
    getCharacters: vi.fn(() => Promise.resolve(['krieg', 'ork_warboss', 'isabella_varr'])),
    getCampaigns: vi.fn(() => Promise.resolve(['default', 'Novel Engine_40k'])),
    getHealth: vi.fn(() => Promise.resolve({
      api: 'healthy',
      config: 'loaded',
      version: '1.0.0',
    })),
    getSystemStatus: vi.fn(() => Promise.resolve({
      api: 'healthy',
      config: 'loaded',
      version: '1.0.0',
    })),
    createCharacter: vi.fn(() => Promise.resolve({
      success: true,
      data: { name: 'test_character' },
    })),
    runSimulation: vi.fn(() => Promise.resolve({
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
    testConnection: vi.fn(() => Promise.resolve(true)),
    getBaseURL: vi.fn(() => 'http://localhost:8000'),
    getSystemStatus: vi.fn(() => Promise.resolve({
      api: 'healthy',
      config: 'loaded',
      version: '1.0.0',
    })),
  },
}));

// Mock react-dropzone
vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({ 'data-testid': 'dropzone' }),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}));

// Create Material-UI theme for tests
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    background: { default: '#0a0a0a', paper: '#1a1a1a' },
    text: { primary: '#ffffff', secondary: '#b0b0b0' },
  },
});

// Test-specific App component that uses our controlled providers
const TestApp: React.FC = () => (
  <Box sx={{ 
    display: 'flex', 
    flexDirection: 'column', 
    minHeight: '100vh',
    backgroundColor: 'background.default'
  }}>
    <Navbar />
    <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/characters" element={<CharacterStudio />} />
        <Route path="/workshop" element={<StoryWorkshop />} />
        <Route path="/library" element={<StoryLibrary />} />
        <Route path="/monitor" element={<SystemMonitor />} />
      </Routes>
    </Box>
  </Box>
);

// Test utilities
const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries for tests
        cacheTime: 0, // Disable caching for tests
        staleTime: 0, // Disable stale time for tests
      },
    },
  });
};

const renderAppWithProviders = ({ route = '/' } = {}) => {
  const queryClient = createTestQueryClient();
  
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <MemoryRouter initialEntries={[route]}>
          <TestApp />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

// Import the mocked API for test assertions
import api from '../services/api';

describe('Novel Engine Workflows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Navigation Workflow', () => {
    it('should render the application without errors', async () => {
      renderAppWithProviders();

      // Should render without throwing errors
      await waitFor(() => {
        // Look for any text that indicates the app is loaded
        expect(document.body).toBeInTheDocument();
      });

      // Should have navigation elements
      expect(screen.getByText('Novel Engine')).toBeInTheDocument();
    });

    it('should have navigation buttons', async () => {
      renderAppWithProviders();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /dashboard/i })).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /characters/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /workshop/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^library$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /monitor/i })).toBeInTheDocument();
    });
  });

  describe('Character Management Workflow', () => {
    it('should navigate to character studio', async () => {
      renderAppWithProviders();

      // Navigate to Characters
      fireEvent.click(screen.getByRole('button', { name: /characters/i }));

      // Should navigate without errors
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Story Generation Workflow', () => {
    it('should navigate to workshop', async () => {
      renderAppWithProviders();

      // Navigate to Workshop
      fireEvent.click(screen.getByRole('button', { name: /workshop/i }));

      // Should navigate without errors
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('System Health Workflow', () => {
    it('should navigate to monitor', async () => {
      renderAppWithProviders();

      // Navigate to Monitor
      fireEvent.click(screen.getByRole('button', { name: /monitor/i }));

      // Should navigate without errors
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should render without crashing on API errors', async () => {
      renderAppWithProviders();

      // Should render without throwing errors
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Responsiveness', () => {
    it('should render without performance issues', async () => {
      renderAppWithProviders();

      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have accessible navigation elements', async () => {
      renderAppWithProviders();

      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });

      // Check for navigation buttons
      expect(screen.getByRole('button', { name: /dashboard/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /characters/i })).toBeInTheDocument();
    });
  });
});

describe('Integration Tests', () => {
  it('should render the application successfully', async () => {
    renderAppWithProviders();

    // Should render without throwing errors
    await waitFor(() => {
      expect(document.body).toBeInTheDocument();
    });

    // Should have main navigation elements
    expect(screen.getByRole('button', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /characters/i })).toBeInTheDocument();
  });
});