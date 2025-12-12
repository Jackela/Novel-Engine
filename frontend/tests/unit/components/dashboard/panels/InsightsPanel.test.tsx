/**
 * InsightsPanel Component Tests
 *
 * Tests cover:
 * 1. Structure and rendering
 * 2. MFD mode switching
 * 3. Quick actions
 * 4. Close button functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock child components to avoid complex dependencies
vi.mock('../../../../../src/features/dashboard/QuickActions', () => ({
  default: ({
    loading,
    error,
    status,
    isLive,
    isOnline,
    onAction,
  }: {
    loading: boolean;
    error: boolean;
    status: string;
    isLive: boolean;
    isOnline: boolean;
    onAction: (action: string) => void;
  }) => (
    <div
      data-testid="quick-actions"
      data-loading={loading}
      data-error={error}
      data-status={status}
      data-live={isLive}
      data-online={isOnline}
    >
      <button onClick={() => onAction('play')}>Play</button>
      QuickActions Mock
    </div>
  ),
}));

vi.mock('../../../../../src/features/dashboard/AnalyticsDashboard', () => ({
  default: ({ loading, error }: { loading: boolean; error: boolean }) => (
    <div data-testid="analytics-dashboard" data-loading={loading} data-error={error}>
      AnalyticsDashboard Mock
    </div>
  ),
}));

vi.mock('../../../../../src/features/dashboard/CharacterNetworks', () => ({
  default: ({ loading, error }: { loading: boolean; error: boolean }) => (
    <div data-testid="character-networks" data-loading={loading} data-error={error}>
      CharacterNetworks Mock
    </div>
  ),
}));

vi.mock('../../../../../src/features/dashboard/NarrativeTimeline', () => ({
  default: ({ loading, error }: { loading: boolean; error: boolean }) => (
    <div data-testid="narrative-timeline" data-loading={loading} data-error={error}>
      NarrativeTimeline Mock
    </div>
  ),
}));

vi.mock('../../../../../src/features/dashboard/EventCascadeFlow', () => ({
  default: ({ loading, error }: { loading: boolean; error: boolean }) => (
    <div data-testid="event-cascade-flow" data-loading={loading} data-error={error}>
      EventCascadeFlow Mock
    </div>
  ),
}));

vi.mock('../../../../../src/features/dashboard/PerformanceMetrics', () => ({
  default: () => <div data-testid="performance-metrics">PerformanceMetrics Mock</div>,
}));

vi.mock('../../../../../src/features/dashboard/SummaryStrip', () => ({
  default: () => <div data-testid="summary-strip">SummaryStrip Mock</div>,
}));

vi.mock('../../../../../src/features/dashboard/MfdModeSelector', () => ({
  default: ({ onChange }: { onChange: (mode: any) => void }) => (
    <div data-testid="mfd-mode-selector">
      <button onClick={() => onChange('analytics')}>DATA</button>
      <button onClick={() => onChange('network')}>NET</button>
      <button onClick={() => onChange('timeline')}>TIME</button>
      <button onClick={() => onChange('signals')}>SIG</button>
    </div>
  ),
}));

import InsightsPanel from '../../../../../src/features/dashboard/panels/InsightsPanel';

describe('InsightsPanel', () => {
  const defaultProps = {
    loading: false,
    error: false,
    pipelineStatus: 'idle' as const,
    isLive: false,
    isOnline: true,
    mfdMode: 'analytics' as const,
    onMfdModeChange: vi.fn(),
    onQuickAction: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Structure', () => {
    it('should render Manual Override section', () => {
      render(<InsightsPanel {...defaultProps} />);

      expect(screen.getByText('Manual Override')).toBeInTheDocument();
    });

    it('should render MFD section', () => {
      render(<InsightsPanel {...defaultProps} />);

      expect(screen.getByText(/MFD \/\//)).toBeInTheDocument();
    });

    it('should display QuickActions component', () => {
      render(<InsightsPanel {...defaultProps} />);

      expect(screen.getByTestId('quick-actions')).toBeInTheDocument();
    });

    it('should have command-panel classes on sections', () => {
      const { container } = render(<InsightsPanel {...defaultProps} />);

      const panels = container.querySelectorAll('.command-panel');
      expect(panels.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('MFD Mode Switching', () => {
    it('should render all MFD mode buttons', () => {
      render(<InsightsPanel {...defaultProps} />);

      expect(screen.getByRole('button', { name: /DATA/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /NET/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /TIME/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /SIG/i })).toBeInTheDocument();
    });

    it('should call onMfdModeChange when mode button clicked', () => {
      const onMfdModeChange = vi.fn();
      render(<InsightsPanel {...defaultProps} onMfdModeChange={onMfdModeChange} />);

      const netButton = screen.getByRole('button', { name: /NET/i });
      fireEvent.click(netButton);

      expect(onMfdModeChange).toHaveBeenCalledWith('network');
    });

    it('should render AnalyticsDashboard when mode is analytics', () => {
      render(<InsightsPanel {...defaultProps} mfdMode="analytics" />);

      expect(screen.getByTestId('analytics-dashboard')).toBeInTheDocument();
    });

    it('should render CharacterNetworks when mode is network', () => {
      render(<InsightsPanel {...defaultProps} mfdMode="network" />);

      expect(screen.getByTestId('character-networks')).toBeInTheDocument();
    });

    it('should render NarrativeTimeline when mode is timeline', () => {
      render(<InsightsPanel {...defaultProps} mfdMode="timeline" />);

      expect(screen.getByTestId('narrative-timeline')).toBeInTheDocument();
    });

    it('should render EventCascadeFlow when mode is signals', () => {
      render(<InsightsPanel {...defaultProps} mfdMode="signals" />);

      expect(screen.getByTestId('event-cascade-flow')).toBeInTheDocument();
    });

    it('should display current mode in MFD header', () => {
      render(<InsightsPanel {...defaultProps} mfdMode="analytics" />);

      expect(screen.getByText(/ANALYTICS/)).toBeInTheDocument();
    });
  });

  describe('Quick Actions', () => {
    it('should pass onQuickAction to QuickActions component', () => {
      const onQuickAction = vi.fn();
      render(<InsightsPanel {...defaultProps} onQuickAction={onQuickAction} />);

      const playButton = screen.getByRole('button', { name: /Play/i });
      fireEvent.click(playButton);

      expect(onQuickAction).toHaveBeenCalledWith('play');
    });

    it('should pass pipeline status to QuickActions', () => {
      render(<InsightsPanel {...defaultProps} pipelineStatus="running" />);

      const quickActions = screen.getByTestId('quick-actions');
      expect(quickActions).toHaveAttribute('data-status', 'running');
    });

    it('should pass isLive to QuickActions', () => {
      render(<InsightsPanel {...defaultProps} isLive={true} />);

      const quickActions = screen.getByTestId('quick-actions');
      expect(quickActions).toHaveAttribute('data-live', 'true');
    });

    it('should pass isOnline to QuickActions', () => {
      render(<InsightsPanel {...defaultProps} isOnline={false} />);

      const quickActions = screen.getByTestId('quick-actions');
      expect(quickActions).toHaveAttribute('data-online', 'false');
    });
  });

  describe('Loading and Error States', () => {
    it('should pass loading prop to QuickActions', () => {
      render(<InsightsPanel {...defaultProps} loading={true} />);

      const quickActions = screen.getByTestId('quick-actions');
      expect(quickActions).toHaveAttribute('data-loading', 'true');
    });

    it('should pass error prop to QuickActions', () => {
      render(<InsightsPanel {...defaultProps} error={true} />);

      const quickActions = screen.getByTestId('quick-actions');
      expect(quickActions).toHaveAttribute('data-error', 'true');
    });

    it('should pass loading prop to MFD content', () => {
      render(<InsightsPanel {...defaultProps} loading={true} mfdMode="analytics" />);

      const analytics = screen.getByTestId('analytics-dashboard');
      expect(analytics).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('Close Button', () => {
    it('should render close button when onClose provided', () => {
      const onClose = vi.fn();
      render(<InsightsPanel {...defaultProps} onClose={onClose} />);

      const closeButton = screen.getByRole('button', { name: /close.*panel/i });
      expect(closeButton).toBeInTheDocument();
    });

    it('should not render close button when onClose not provided', () => {
      render(<InsightsPanel {...defaultProps} />);

      const closeButton = screen.queryByRole('button', { name: /close.*panel/i });
      expect(closeButton).not.toBeInTheDocument();
    });

    it('should call onClose when close button clicked', () => {
      const onClose = vi.fn();
      render(<InsightsPanel {...defaultProps} onClose={onClose} />);

      const closeButton = screen.getByRole('button', { name: /close.*panel/i });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });
});
