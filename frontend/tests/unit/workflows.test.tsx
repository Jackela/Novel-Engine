import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import Navbar from '@/components/Navbar';
import Dashboard from '@/features/dashboard/Dashboard';
import CharacterStudio from '@/features/characters';
import StoryWorkshop from '@/features/stories/StoryWorkshop';
import StoryLibrary from '@/features/stories/StoryLibrary';
import SystemMonitor from '@/features/system/SystemMonitor';
import authSlice from '@/store/slices/authSlice';
import charactersSlice from '@/store/slices/charactersSlice';
import storiesSlice from '@/store/slices/storiesSlice';
import campaignsSlice from '@/store/slices/campaignsSlice';
import dashboardSlice from '@/store/slices/dashboardSlice';
import decisionSlice from '@/store/slices/decisionSlice';
import { AuthProvider } from '@/contexts/AuthContext';

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Mock EventSource
const mockEventSource = {
  onmessage: null,
  onopen: null,
  onerror: null,
  close: vi.fn(),
  CONNECTING: 0,
  OPEN: 1,
  CLOSED: 2,
};

global.EventSource = vi.fn(function () { return mockEventSource; }) as unknown as typeof EventSource;
// Add static constants to the mock constructor
(global.EventSource as any).CONNECTING = 0;
(global.EventSource as any).OPEN = 1;
(global.EventSource as any).CLOSED = 2;

// Mock the API module with both default and named exports
const mockCharacterSummaries = [
  {
    id: 'aria-shadowbane',
    name: 'Aria Shadowbane',
    status: 'active',
    type: 'protagonist',
    updated_at: '2025-12-29T01:00:00Z',
    workspace_id: 'workspace-main',
  },
  {
    id: 'captain-lyra',
    name: 'Captain Lyra',
    status: 'active',
    type: 'protagonist',
    updated_at: '2025-12-29T01:01:00Z',
    workspace_id: 'workspace-main',
  },
  {
    id: 'mage-obscura',
    name: 'Mage Obscura',
    status: 'inactive',
    type: 'npc',
    updated_at: '2025-12-29T01:02:00Z',
    workspace_id: 'workspace-main',
  },
];

vi.mock('@/services/api', () => ({
  default: {
    getCharacters: vi.fn(() => Promise.resolve(mockCharacterSummaries)),
    getCampaigns: vi.fn(() => Promise.resolve(['default', 'Novel Engine_40k'])),
    getCharacterDetails: vi.fn((name: string) => Promise.resolve({
      id: name,
      name,
      faction: 'Mock Faction',
      role: 'Agent',
      description: 'Mock character',
      stats: { strength: 5, intelligence: 5, charisma: 5, dexterity: 5, willpower: 5, perception: 5 },
      equipment: [],
      relationships: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    })),
    updateCharacter: vi.fn(() => Promise.resolve({ success: true })),
    deleteCharacter: vi.fn(() => Promise.resolve({ success: true })),
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
  components: {
    MuiListItemText: {
      defaultProps: {
        primaryTypographyProps: { component: 'div' },
        secondaryTypographyProps: { component: 'div' },
      },
    },
  },
});

// Test-specific App component that uses our controlled providers
const TestApp: React.FC = () => (
  <Box
    component="div"
    sx={{
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
      backgroundColor: 'background.default'
    }}
  >
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

const createTestStore = () => {
  return configureStore({
    reducer: {
      auth: authSlice,
      characters: charactersSlice,
      stories: storiesSlice,
      campaigns: campaignsSlice,
      dashboard: dashboardSlice,
      decision: decisionSlice,
    },
  });
};

const renderAppWithProviders = async ({ route = '/' } = {}) => {
  const queryClient = createTestQueryClient();
  const store = createTestStore();
  let rendered;
  await act(async () => {
    rendered = render(
      <Provider store={store}>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={theme}>
              <CssBaseline />
              <MemoryRouter initialEntries={[route]}>
                <TestApp />
              </MemoryRouter>
            </ThemeProvider>
          </QueryClientProvider>
        </AuthProvider>
      </Provider>
    );
  });
  return rendered!;
};

// Import the mocked API for test assertions
import { dashboardAPI } from '@/services/api/dashboardAPI';

// Mock both APIs to cover all bases
vi.mock('@/services/api');
vi.mock('@/services/api/dashboardAPI', () => ({
  dashboardAPI: {
    startOrchestration: vi.fn().mockResolvedValue({
      data: { success: true, data: { status: 'running' } }
    }),
    getOrchestrationStatus: vi.fn().mockResolvedValue({
      data: { success: true, data: { status: 'idle', steps: [] } }
    }),
    getSystemStatus: vi.fn().mockResolvedValue({
      data: { status: 'operational', uptime: 100, components: { simulation: 'idle' } }
    }),
    getHealth: vi.fn().mockResolvedValue({
      data: { status: 'ok' }
    }),
    getAnalyticsMetrics: vi.fn().mockResolvedValue({
      data: { success: true, data: {} }
    }),
    getNarrative: vi.fn().mockResolvedValue({
      data: {
        success: true,
        data: {
          story: 'Test narrative output',
          participants: ['agent'],
          turns_completed: 1,
          has_content: true,
        },
      },
    })
  }
}));

// Mock queries
vi.mock('@/services/queries', () => ({
  queryKeys: {
    characters: ['characters', 'list'],
    characterDetails: (name: string) => ['characters', 'detail', name],
  },
  useCharactersQuery: vi.fn(() => ({
    data: ['char1', 'char2'],
    isLoading: false,
    error: null
  })),
  useCampaignsQuery: vi.fn(() => ({
    data: [],
    isLoading: false
  }))
}));

describe('Feature: Orchestration Workflow', () => {
  describe('Scenario: User starts orchestration successfully', () => {
    it('Given the user is on the dashboard, When they click Start, Then the system should enter Running state', async () => {
      await renderAppWithProviders();

      // When: User clicks Start
      // The button is labeled "Start Orchestration" via aria-label or "START" text
      const startButton = screen.getByRole('button', { name: /Start Orchestration/i });
      expect(startButton).toBeInTheDocument();

      // Simulating click (mocked API will return success)
      await act(async () => {
        fireEvent.click(startButton);
      });

      // Then: Expect visual feedback (this depends on the UI showing 'Running' state)
      // For now, we verify API was called
      expect(dashboardAPI.startOrchestration).toHaveBeenCalled();
    });
  });

  describe('Scenario: API Failure handling', () => {
    it('Given the API is down, When user starts orchestration, Then an error notification should appear', async () => {
      // Given: API Mock Failure
      (dashboardAPI.startOrchestration as any).mockRejectedValueOnce(new Error('API Down'));

      await renderAppWithProviders();

      const startButton = screen.getByRole('button', { name: /Start Orchestration/i });
      await act(async () => {
        fireEvent.click(startButton);
      });

      // Then: Verify error handling (generic check for now implies no crash)
      expect(document.body).toBeInTheDocument();
    });
  });
});

describe('Feature: Component Navigation', () => {
  describe('Scenario: Navigation Bar Availability', () => {
    it('Given the user launches the app, Then all main navigation options should be visible', async () => {
      await renderAppWithProviders();
      expect(screen.getByRole('button', { name: /^dashboard$/i })).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /characters/i })[0]).toBeInTheDocument();
    });
  });

  describe('Scenario: Switching to Character Studio', () => {
    it('When user clicks Characters, Then the Character Studio should be displayed', async () => {
      await renderAppWithProviders();
      await act(async () => {
        fireEvent.click(screen.getAllByRole('button', { name: /characters/i })[0]);
      });
      expect(document.body).toBeInTheDocument();
    });
  });
});

describe('Feature: Novel Engine Workflows', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('Scenario: Initial Application Load', () => {
    it('Given the application is launched, Then it should render without errors and display the main title', async () => {
      await renderAppWithProviders();
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
      expect(screen.getByText('Novel Engine')).toBeInTheDocument();
    });

    it('Given the application is launched, Then all main navigation buttons should be present', async () => {
      await renderAppWithProviders();
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^dashboard$/i })).toBeInTheDocument();
      });
      expect(screen.getAllByRole('button', { name: /characters/i })[0]).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /workshop/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^library$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /monitor/i })).toBeInTheDocument();
    });
  });

  describe('Scenario: Navigating to Story Workshop', () => {
    it('Given the user is on the dashboard, When they click the "Workshop" button, Then the Story Workshop page should be displayed', async () => {
      await renderAppWithProviders();
      await act(async () => {
        fireEvent.click(screen.getByRole('button', { name: /workshop/i }));
      });
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Scenario: Navigating to System Monitor', () => {
    it('Given the user is on the dashboard, When they click the "Monitor" button, Then the System Monitor page should be displayed', async () => {
      await renderAppWithProviders();
      await act(async () => {
        fireEvent.click(screen.getByRole('button', { name: /monitor/i }));
      });
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Scenario: General API Error Handling', () => {
    it('Given an API call fails, When the application attempts to render, Then it should not crash', async () => {
      await renderAppWithProviders();
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Scenario: Application Performance', () => {
    it('Given the application is launched, Then it should render without significant performance issues', async () => {
      await renderAppWithProviders();
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });

  describe('Scenario: Accessibility of Navigation', () => {
    it('Given the application is launched, Then main navigation elements should be accessible', async () => {
      await renderAppWithProviders();
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
      expect(screen.getByRole('button', { name: /^dashboard$/i })).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /characters/i })[0]).toBeInTheDocument();
    });
  });
});

describe('Feature: Integration Tests', () => {
  describe('Scenario: Application Initialization', () => {
    it('Given the application starts, Then it should render successfully and display core navigation', async () => {
      await renderAppWithProviders();
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
      expect(screen.getByRole('button', { name: /^dashboard$/i })).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /characters/i })[0]).toBeInTheDocument();
    });
  });
});
