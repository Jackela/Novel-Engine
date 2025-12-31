import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import type * as ReactRouterDom from 'react-router-dom';
import { vi, describe, it, expect, afterEach } from 'vitest';
import LandingPage from '../LandingPage';

const mockNavigate = vi.hoisted(() => vi.fn());
const mockEnterGuestMode = vi.hoisted(() => vi.fn());

vi.mock('react-router-dom', async () => {
  const actual: typeof ReactRouterDom = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuthContext: () => ({
    isAuthenticated: false,
    isLoading: false,
    error: null,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
    enterGuestMode: mockEnterGuestMode,
  }),
}));

function renderLandingPage() {
  const theme = createTheme();
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    </ThemeProvider>
  );
}

describe('LandingPage', () => {
  afterEach(() => {
    mockNavigate.mockClear();
    mockEnterGuestMode.mockClear();
  });

  it('calls enterGuestMode when Launch Engine is clicked', () => {
    renderLandingPage();

    const launchButton = screen.getByRole('button', { name: /launch engine/i });
    fireEvent.click(launchButton);

    expect(mockEnterGuestMode).toHaveBeenCalled();
  });

  it('renders the main title', () => {
    renderLandingPage();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/NARRATIVE.*ENGINE/i);
  });

  it('renders the feature cards', () => {
    renderLandingPage();

    expect(screen.getByText(/Live Orchestration/i)).toBeInTheDocument();
    expect(screen.getByText(/Adaptive Analytics/i)).toBeInTheDocument();
    expect(screen.getByText(/Secure Environment/i)).toBeInTheDocument();
  });
});
