/**
 * Dashboard Layout Component Tests
 *
 * TDD: RED phase - Writing tests before implementation
 *
 * Tests cover:
 * 1. Layout structure (sidebar, main, aside)
 * 2. Responsive behavior
 * 3. Panel visibility toggling
 * 4. Accessibility requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '@/styles/theme';

// Component to be implemented
import DashboardLayout from '@/components/dashboard/DashboardLayout';

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const renderWithTheme = (component: React.ReactElement) => {
  return render(component, { wrapper: TestWrapper });
};

describe('DashboardLayout', () => {
  describe('Structure', () => {
    it('should render three-region layout: sidebar, main, aside', () => {
      renderWithTheme(
        <DashboardLayout
          sidebar={<div data-testid="sidebar-content">Sidebar</div>}
          main={<div data-testid="main-content">Main</div>}
          aside={<div data-testid="aside-content">Aside</div>}
        />
      );

      expect(screen.getByTestId('sidebar-content')).toBeInTheDocument();
      expect(screen.getByTestId('main-content')).toBeInTheDocument();
      expect(screen.getByTestId('aside-content')).toBeInTheDocument();
    });

    it('should have proper landmark roles for accessibility', () => {
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
        />
      );

      // Main content area should have main role
      expect(screen.getByRole('main')).toBeInTheDocument();

      // Sidebar should have complementary or navigation role
      expect(screen.getByRole('complementary', { name: /engine/i })).toBeInTheDocument();

      // Aside should have complementary role
      expect(screen.getByRole('complementary', { name: /insights/i })).toBeInTheDocument();
    });

    it('should apply correct layout container class', () => {
      const { container } = renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
        />
      );

      expect(container.querySelector('.dashboard-layout')).toBeInTheDocument();
    });
  });

  describe('Panel Visibility', () => {
    it('should allow sidebar to be toggled', () => {
      const onSidebarToggle = vi.fn();

      renderWithTheme(
        <DashboardLayout
          sidebar={<div data-testid="sidebar-content">Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={true}
          onSidebarToggle={onSidebarToggle}
        />
      );

      // Find and click sidebar toggle button (updated aria-label)
      const toggleButton = screen.getByRole('button', { name: /hide.*engine/i });
      fireEvent.click(toggleButton);

      expect(onSidebarToggle).toHaveBeenCalledWith(false);
    });

    it('should allow aside to be toggled', () => {
      const onAsideToggle = vi.fn();

      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div data-testid="aside-content">Aside</div>}
          asideOpen={true}
          onAsideToggle={onAsideToggle}
        />
      );

      const toggleButton = screen.getByRole('button', { name: /hide.*insights/i });
      fireEvent.click(toggleButton);

      expect(onAsideToggle).toHaveBeenCalledWith(false);
    });

    it('should hide sidebar content when sidebarOpen is false', () => {
      renderWithTheme(
        <DashboardLayout
          sidebar={<div data-testid="sidebar-content">Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={false}
        />
      );

      // Sidebar content should not be in the document when closed
      expect(screen.queryByTestId('sidebar-content')).not.toBeInTheDocument();
    });

    it('should hide aside content when asideOpen is false', () => {
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div data-testid="aside-content">Aside</div>}
          asideOpen={false}
        />
      );

      // Aside content should not be in the document when closed
      expect(screen.queryByTestId('aside-content')).not.toBeInTheDocument();
    });
  });

  describe('Sizing', () => {
    it('should render sidebar and aside regions', () => {
      const { container } = renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
        />
      );

      const sidebar = container.querySelector('.dashboard-sidebar');
      const aside = container.querySelector('.dashboard-aside');
      const main = container.querySelector('.dashboard-main');

      // Regions should exist
      expect(sidebar).toBeInTheDocument();
      expect(aside).toBeInTheDocument();
      expect(main).toBeInTheDocument();
    });

    it('should render main region when panels are hidden', () => {
      const { container } = renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={false}
          asideOpen={false}
        />
      );

      const main = container.querySelector('.dashboard-main');
      // Main should still exist
      expect(main).toBeInTheDocument();
    });
  });

  describe('Spacing', () => {
    it('should render layout container with class', () => {
      const { container } = renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
        />
      );

      const layout = container.querySelector('.dashboard-layout');
      expect(layout).toBeInTheDocument();
    });
  });

  describe('Animation', () => {
    it('should have data-state attribute when open', () => {
      const { container } = renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={true}
        />
      );

      const sidebar = container.querySelector('.dashboard-sidebar');
      expect(sidebar).toHaveAttribute('data-state', 'open');
    });

    it('should have data-state closing when panel is closed', () => {
      const { container } = renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={false}
        />
      );

      const sidebar = container.querySelector('.dashboard-sidebar');
      // When closed, sidebar still exists but with closing state
      expect(sidebar).toHaveAttribute('data-state', 'closing');
    });
  });

  describe('Keyboard Navigation', () => {
    it('should call onSidebarToggle(false) when Cmd+[ pressed with sidebar open', () => {
      const onSidebarToggle = vi.fn();
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={true}
          onSidebarToggle={onSidebarToggle}
        />
      );

      fireEvent.keyDown(document.body, { key: '[', metaKey: true });
      expect(onSidebarToggle).toHaveBeenCalledWith(false);
    });

    it('should call onSidebarToggle(true) when Cmd+[ pressed with sidebar closed', () => {
      const onSidebarToggle = vi.fn();
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={false}
          onSidebarToggle={onSidebarToggle}
        />
      );

      fireEvent.keyDown(document.body, { key: '[', metaKey: true });
      expect(onSidebarToggle).toHaveBeenCalledWith(true);
    });

    it('should call onAsideToggle(false) when Cmd+] pressed with aside open', () => {
      const onAsideToggle = vi.fn();
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          asideOpen={true}
          onAsideToggle={onAsideToggle}
        />
      );

      fireEvent.keyDown(document.body, { key: ']', metaKey: true });
      expect(onAsideToggle).toHaveBeenCalledWith(false);
    });

    it('should call onAsideToggle(true) when Cmd+] pressed with aside closed', () => {
      const onAsideToggle = vi.fn();
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          asideOpen={false}
          onAsideToggle={onAsideToggle}
        />
      );

      fireEvent.keyDown(document.body, { key: ']', metaKey: true });
      expect(onAsideToggle).toHaveBeenCalledWith(true);
    });

    it('should not trigger toggle without meta key', () => {
      const onSidebarToggle = vi.fn();
      const onAsideToggle = vi.fn();
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={true}
          asideOpen={true}
          onSidebarToggle={onSidebarToggle}
          onAsideToggle={onAsideToggle}
        />
      );

      fireEvent.keyDown(document.body, { key: '[' });
      fireEvent.keyDown(document.body, { key: ']' });

      expect(onSidebarToggle).not.toHaveBeenCalled();
      expect(onAsideToggle).not.toHaveBeenCalled();
    });

    it('should support Ctrl key as alternative to Cmd key', () => {
      const onSidebarToggle = vi.fn();
      const onAsideToggle = vi.fn();
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={true}
          asideOpen={true}
          onSidebarToggle={onSidebarToggle}
          onAsideToggle={onAsideToggle}
        />
      );

      fireEvent.keyDown(document.body, { key: '[', ctrlKey: true });
      expect(onSidebarToggle).toHaveBeenCalledWith(false);

      fireEvent.keyDown(document.body, { key: ']', ctrlKey: true });
      expect(onAsideToggle).toHaveBeenCalledWith(false);
    });
  });
});

describe('DashboardLayout - Show Panel Buttons', () => {
  it('should render "Show engine panel" button when sidebar closed', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        sidebarOpen={false}
      />
    );

    expect(screen.getByRole('button', { name: /show.*engine/i })).toBeInTheDocument();
  });

  it('should render "Show insights panel" button when aside closed', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        asideOpen={false}
      />
    );

    expect(screen.getByRole('button', { name: /show.*insights/i })).toBeInTheDocument();
  });

  it('should call onSidebarToggle(true) when show engine clicked', () => {
    const onSidebarToggle = vi.fn();
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        sidebarOpen={false}
        onSidebarToggle={onSidebarToggle}
      />
    );

    const showButton = screen.getByRole('button', { name: /show.*engine/i });
    fireEvent.click(showButton);

    expect(onSidebarToggle).toHaveBeenCalledWith(true);
  });

  it('should call onAsideToggle(true) when show insights clicked', () => {
    const onAsideToggle = vi.fn();
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        asideOpen={false}
        onAsideToggle={onAsideToggle}
      />
    );

    const showButton = screen.getByRole('button', { name: /show.*insights/i });
    fireEvent.click(showButton);

    expect(onAsideToggle).toHaveBeenCalledWith(true);
  });
});

describe('DashboardLayout - ARIA Labels', () => {
  it('should have correct aria-label on sidebar region', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
      />
    );

    const sidebar = screen.getByRole('complementary', { name: /engine/i });
    expect(sidebar).toHaveAttribute('aria-label', 'Engine panel');
  });

  it('should have correct aria-label on aside region', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
      />
    );

    const aside = screen.getByRole('complementary', { name: /insights/i });
    expect(aside).toHaveAttribute('aria-label', 'Insights panel');
  });

  it('should have aria-hidden=true when sidebar is closed', () => {
    const { container } = renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        sidebarOpen={false}
      />
    );

    const sidebar = container.querySelector('.dashboard-sidebar');
    expect(sidebar).toHaveAttribute('aria-hidden', 'true');
  });

  it('should have aria-hidden=true when aside is closed', () => {
    const { container } = renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        asideOpen={false}
      />
    );

    const aside = container.querySelector('.dashboard-aside');
    expect(aside).toHaveAttribute('aria-hidden', 'true');
  });

  it('should have aria-describedby for keyboard shortcut hints on sidebar toggle', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        sidebarOpen={true}
      />
    );

    const hideButton = screen.getByRole('button', { name: /hide.*engine/i });
    expect(hideButton).toHaveAttribute('aria-describedby', 'shortcut-sidebar');
  });

  it('should have aria-describedby for keyboard shortcut hints on aside toggle', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        asideOpen={true}
      />
    );

    const hideButton = screen.getByRole('button', { name: /hide.*insights/i });
    expect(hideButton).toHaveAttribute('aria-describedby', 'shortcut-aside');
  });

  it('should have visually hidden shortcut hints for screen readers', () => {
    const { container } = renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        sidebarOpen={true}
        asideOpen={true}
      />
    );

    const sidebarHint = container.querySelector('#shortcut-sidebar');
    const asideHint = container.querySelector('#shortcut-aside');

    expect(sidebarHint).toBeInTheDocument();
    expect(sidebarHint).toHaveTextContent(/Cmd\+\[|Ctrl\+\[/);
    expect(asideHint).toBeInTheDocument();
    expect(asideHint).toHaveTextContent(/Cmd\+\]|Ctrl\+\]/);
  });
});

describe('DashboardLayout - Edge Cases', () => {
  it('should handle both panels closed simultaneously', () => {
    const { container } = renderWithTheme(
      <DashboardLayout
        sidebar={<div data-testid="sidebar-content">Sidebar</div>}
        main={<div data-testid="main-content">Main</div>}
        aside={<div data-testid="aside-content">Aside</div>}
        sidebarOpen={false}
        asideOpen={false}
      />
    );

    // Both show buttons should be visible
    expect(screen.getByRole('button', { name: /show.*engine/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /show.*insights/i })).toBeInTheDocument();

    // Main content should still be visible
    expect(screen.getByTestId('main-content')).toBeInTheDocument();

    // Panel contents should not be visible
    expect(screen.queryByTestId('sidebar-content')).not.toBeInTheDocument();
    expect(screen.queryByTestId('aside-content')).not.toBeInTheDocument();
  });

  it('should handle undefined toggle callbacks gracefully', () => {
    // Should not throw when callbacks are undefined
    expect(() => {
      renderWithTheme(
        <DashboardLayout
          sidebar={<div>Sidebar</div>}
          main={<div>Main</div>}
          aside={<div>Aside</div>}
          sidebarOpen={true}
          asideOpen={true}
          // No toggle callbacks provided
        />
      );
    }).not.toThrow();
  });

  it('should render with custom className', () => {
    const { container } = renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
        className="custom-class"
      />
    );

    expect(container.querySelector('.dashboard-layout.custom-class')).toBeInTheDocument();
  });
});

// Mobile responsive tests are skipped in jsdom because MUI's useMediaQuery
// requires a real browser environment. These are covered by E2E tests.
describe.skip('DashboardLayout - Mobile Responsive', () => {
  beforeEach(() => {
    // Mock mobile viewport - note: MUI useMediaQuery doesn't work well with mocks
    vi.stubGlobal('matchMedia', vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('max-width'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })));
  });

  it('should render tabbed layout on mobile', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        aside={<div>Aside</div>}
      />
    );

    // Should have tab navigation instead of three columns
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /engine/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /world/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /insights/i })).toBeInTheDocument();
  });

  it('should show only active tab content on mobile', () => {
    renderWithTheme(
      <DashboardLayout
        sidebar={<div data-testid="sidebar-content">Sidebar</div>}
        main={<div data-testid="main-content">Main</div>}
        aside={<div data-testid="aside-content">Aside</div>}
      />
    );

    // Default tab should be World (main content)
    expect(screen.getByTestId('main-content')).toBeVisible();
    expect(screen.queryByTestId('sidebar-content')).not.toBeVisible();
    expect(screen.queryByTestId('aside-content')).not.toBeVisible();
  });
});
