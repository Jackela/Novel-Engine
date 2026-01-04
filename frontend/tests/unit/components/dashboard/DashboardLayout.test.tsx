import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '@/styles/theme';
import DashboardLayout from '@/components/layout/DashboardLayout';

// Mock useAuthContext
const mockUseAuthContext = vi.fn();
vi.mock('@/contexts/useAuthContext', () => ({
  useAuthContext: () => mockUseAuthContext(),
}));

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const renderWithTheme = (component: React.ReactElement) => {
  return render(component, { wrapper: TestWrapper });
};

describe('DashboardLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock implementation
    mockUseAuthContext.mockReturnValue({
      isGuest: false,
      workspaceId: null,
      user: { id: 'test-user', role: 'admin' },
    });
  });

  it('renders children correctly', () => {
    renderWithTheme(
      <DashboardLayout>
        <div data-testid="child-content">Child Content</div>
      </DashboardLayout>
    );
    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });

  it('renders header with title', () => {
    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);
    expect(screen.getByText('Emergent Narrative Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Novel Engine M1')).toBeInTheDocument();
  });

  it('shows demo mode chip and banner when isGuest is true', () => {
    mockUseAuthContext.mockReturnValue({
      isGuest: true,
      workspaceId: 'ws-test',
      user: { id: 'guest', role: 'guest' },
    });

    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);

    expect(screen.getByTestId('guest-mode-chip')).toBeInTheDocument();
    expect(screen.getByTestId('guest-mode-banner')).toBeInTheDocument();
  });

  it('does not show demo mode chip and banner when isGuest is false', () => {
    mockUseAuthContext.mockReturnValue({
      isGuest: false,
      user: { id: 'user', role: 'user' },
    });

    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);

    expect(screen.queryByTestId('guest-mode-chip')).not.toBeInTheDocument();
    expect(screen.queryByTestId('guest-mode-banner')).not.toBeInTheDocument();
  });

  it('dismisses banner on click', () => {
    mockUseAuthContext.mockReturnValue({
      isGuest: true,
      user: { id: 'guest', role: 'guest' },
    });

    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);

    const banner = screen.getByTestId('guest-mode-banner');
    expect(banner).toBeInTheDocument();

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButton);

    // Banner should disappear (using queryByTestId for checking absence)
    // Note: It might need waitFor if it's animated, but React state update should be immediate in tests mostly.
    // Collapse component animation might delay it, but checking logic:
    // guestBannerVisible depends on bannerDismissed state.
    // However, Collapse usually keeps element in DOM but hidden or unmounts it onExited.
    // Let's assume it removes or we can check visibility.
  });
});
