import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '@/styles/theme';

const guestBannerKey = 'novel-engine-guest-banner-dismissed';
const mockUseAuthContext = vi.hoisted(() =>
  vi.fn(() => ({
    isGuest: false,
    workspaceId: null,
  }))
);

vi.mock('@/contexts/useAuthContext', () => ({
  useAuthContext: mockUseAuthContext,
}));

import DashboardLayout from '@/components/layout/DashboardLayout';

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
    window.localStorage.removeItem(guestBannerKey);
    // Default mock implementation
    mockUseAuthContext.mockReturnValue({
      isGuest: false,
      workspaceId: null,
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
    });

    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);

    expect(screen.getByTestId('guest-mode-chip')).toBeInTheDocument();
    expect(screen.getByTestId('guest-mode-banner')).toBeInTheDocument();
  });

  it('does not show demo mode chip and banner when isGuest is false', () => {
    mockUseAuthContext.mockReturnValue({
      isGuest: false,
    });

    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);

    expect(screen.queryByTestId('guest-mode-chip')).not.toBeInTheDocument();
    expect(screen.queryByTestId('guest-mode-banner')).not.toBeInTheDocument();
  });

  it('dismisses banner on click', () => {
    mockUseAuthContext.mockReturnValue({
      isGuest: true,
    });

    renderWithTheme(<DashboardLayout>Content</DashboardLayout>);

    const banner = screen.getByTestId('guest-mode-banner');
    expect(banner).toBeInTheDocument();

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButton);

    expect(window.localStorage.getItem(guestBannerKey)).toBe('1');
  });
});
