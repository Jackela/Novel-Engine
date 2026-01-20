import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, afterEach } from 'vitest';
import LandingPage from '../LandingPage';

const mockNavigate = vi.hoisted(() => vi.fn());
const mockLoginAsGuest = vi.hoisted(() => vi.fn());

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('@/features/auth', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    isLoading: false,
    error: null,
    loginAsGuest: mockLoginAsGuest,
  }),
}));

describe('LandingPage', () => {
  afterEach(() => {
    mockNavigate.mockClear();
    mockLoginAsGuest.mockClear();
  });

  it('calls loginAsGuest when Launch Engine is clicked', () => {
    render(<LandingPage />);

    const launchButton = screen.getByRole('button', { name: /launch engine/i });
    fireEvent.click(launchButton);

    expect(mockLoginAsGuest).toHaveBeenCalledTimes(1);
  });

  it('renders the main title', () => {
    render(<LandingPage />);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /Narrative Engine/i
    );
  });

  it('renders the feature cards', () => {
    render(<LandingPage />);

    expect(screen.getByText(/Live Orchestration/i)).toBeInTheDocument();
    expect(screen.getByText(/Adaptive Analytics/i)).toBeInTheDocument();
    expect(screen.getByText(/Secure Environment/i)).toBeInTheDocument();
  });
});
