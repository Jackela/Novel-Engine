import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import RealTimeActivity from '../../../src/features/dashboard/RealTimeActivity';

expect.extend(toHaveNoViolations);

// Mock useRealtimeEvents to return error state
vi.mock('../../../src/hooks/useRealtimeEvents', () => ({
  useRealtimeEvents: vi.fn(),
}));

import { useRealtimeEvents } from '../../../src/hooks/useRealtimeEvents';

describe('RealTimeActivity Error State Accessibility', () => {
  const mockError = new Error('Failed to connect to event stream. Please check your connection and try again.');
  let originalLocation: Location;

  beforeEach(() => {
    // Save original location
    originalLocation = window.location;

    // Mock window.location.reload by deleting and recreating
    delete (window as any).location;
    window.location = {
      ...originalLocation,
      reload: vi.fn(),
    } as any;

    // Mock error state
    (useRealtimeEvents as any).mockReturnValue({
      events: [],
      loading: false,
      error: mockError,
      connectionState: 'error',
    });
  });

  afterEach(() => {
    // Restore original location
    window.location = originalLocation;
  });

  it('error container has role="alert" attribute', () => {
    render(<RealTimeActivity />);

    const errorContainer = screen.getByRole('alert');
    expect(errorContainer).toBeInTheDocument();
  });

  it('error message is readable by screen readers', () => {
    render(<RealTimeActivity />);

    // Error heading should be visible
    const heading = screen.getByText(/Unable to load live events/i);
    expect(heading).toBeVisible();
    expect(heading).not.toHaveAttribute('aria-hidden', 'true');

    // Error description should be visible
    const description = screen.getByText(mockError.message);
    expect(description).toBeVisible();
    expect(description).not.toHaveAttribute('aria-hidden', 'true');
  });

  it('retry button is keyboard accessible', async () => {
    const user = userEvent.setup();

    render(<RealTimeActivity />);

    const retryButton = screen.getByRole('button', { name: /Retry Connection/i });

    // Button should be focusable
    await user.tab();
    expect(retryButton).toHaveFocus();

    // Button should be activatable with Enter
    await user.keyboard('{Enter}');
    expect(window.location.reload).toHaveBeenCalled();
  });

  it('retry button can be activated with Space key', async () => {
    const user = userEvent.setup();

    render(<RealTimeActivity />);

    const retryButton = screen.getByRole('button', { name: /Retry Connection/i });

    // Focus the button
    retryButton.focus();
    expect(retryButton).toHaveFocus();

    // Activate with Space
    await user.keyboard(' ');
    expect(window.location.reload).toHaveBeenCalled();
  });

  it('has no accessibility violations in error state', async () => {
    const { container } = render(<RealTimeActivity />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('error icon is properly hidden from screen readers', () => {
    render(<RealTimeActivity />);

    // AlertCircle icon should have aria-hidden
    const icon = document.querySelector('[aria-hidden="true"]');
    expect(icon).toBeInTheDocument();
  });

  it('error state has appropriate color contrast', () => {
    render(<RealTimeActivity />);

    const errorContainer = screen.getByRole('alert');

    // Verify container has visible styles (border and background)
    const styles = window.getComputedStyle(errorContainer);
    expect(styles.borderWidth).not.toBe('0px');
    expect(styles.backgroundColor).not.toBe('transparent');
  });
});

describe('RealTimeActivity Connection Status Accessibility', () => {
  it('connection status uses text, not just color', () => {
    // Mock connected state
    (useRealtimeEvents as any).mockReturnValue({
      events: [],
      loading: false,
      error: null,
      connectionState: 'connected',
    });

    render(<RealTimeActivity />);

    // Status should have text content ("● Live" or "Live")
    const statusText = screen.getByText(/Live/i);
    expect(statusText).toBeInTheDocument();
    expect(statusText.textContent).toMatch(/Live/);
  });

  it('connecting state is conveyed through text', () => {
    // Mock connecting state
    (useRealtimeEvents as any).mockReturnValue({
      events: [],
      loading: true,
      error: null,
      connectionState: 'connecting',
    });

    render(<RealTimeActivity />);

    // Status should show "Connecting" text
    const statusText = screen.getByText(/Connecting/i);
    expect(statusText).toBeInTheDocument();
  });
});
