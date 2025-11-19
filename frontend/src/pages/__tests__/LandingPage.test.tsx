import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import type * as ReactRouterDom from 'react-router-dom';
import { vi } from 'vitest';
import LandingPage from '../LandingPage';

const mockEnterGuestMode = vi.hoisted(() => vi.fn());
const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock('../../contexts/AuthContext', () => ({
  useAuthContext: () => ({
    isAuthenticated: false,
    isGuest: false,
    enterGuestMode: mockEnterGuestMode,
  }),
}));

vi.mock('react-router-dom', async () => {
  const actual: typeof ReactRouterDom = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

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

describe('LandingPage CTAs', () => {
  afterEach(() => {
    mockEnterGuestMode.mockClear();
    mockNavigate.mockClear();
  });

  it('renders the Request Access CTA with the ops@ mailto link', () => {
    renderLandingPage();

    const requestAccess = screen.getByRole('link', { name: /request access/i });
    expect(requestAccess).toHaveAttribute('href', 'mailto:ops@novel-engine.ai?subject=Novel%20Engine%20Access');
  });

  it('enters guest mode and navigates to the dashboard when View Demo is clicked', () => {
    renderLandingPage();

    const demoButton = screen.getByRole('button', { name: /view demo/i });
    fireEvent.click(demoButton);

    expect(mockEnterGuestMode).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
  });
});
