/**
 * EnginePanel Component Tests
 *
 * Tests cover:
 * 1. Structure and rendering
 * 2. Loading states
 * 3. Error states
 * 4. Close button functionality
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock child components to avoid complex dependencies
vi.mock('../../../../../src/features/dashboard/TurnPipelineStatus', () => ({
  default: ({ loading, error, status, isLive }: { loading: boolean; error: boolean; status: string; isLive: boolean }) => (
    <div
      data-testid="turn-pipeline-status"
      data-loading={loading}
      data-error={error}
      data-status={status}
      data-live={isLive}
    >
      TurnPipelineStatus Mock
    </div>
  ),
}));

vi.mock('../../../../../src/features/dashboard/RealTimeActivity', () => ({
  default: ({ loading, error, density }: { loading: boolean; error: boolean; density: string }) => (
    <div
      data-testid="real-time-activity"
      data-loading={loading}
      data-error={error}
      data-density={density}
    >
      RealTimeActivity Mock
    </div>
  ),
}));

import EnginePanel from '../../../../../src/features/dashboard/panels/EnginePanel';

describe('EnginePanel', () => {
  const defaultProps = {
    loading: false,
    error: false,
    pipelineStatus: 'idle' as const,
    isLive: false,
  };

  describe('Structure', () => {
    it('should render Simulation Pipeline section', () => {
      render(<EnginePanel {...defaultProps} />);

      expect(screen.getByText('Simulation Pipeline')).toBeInTheDocument();
    });

    it('should render Activity Stream section', () => {
      render(<EnginePanel {...defaultProps} />);

      expect(screen.getByText('Activity Stream')).toBeInTheDocument();
    });

    it('should display TurnPipelineStatus component', () => {
      render(<EnginePanel {...defaultProps} />);

      expect(screen.getByTestId('turn-pipeline-status')).toBeInTheDocument();
    });

    it('should display RealTimeActivity component', () => {
      render(<EnginePanel {...defaultProps} />);

      expect(screen.getByTestId('real-time-activity')).toBeInTheDocument();
    });

    it('should have command-panel classes on sections', () => {
      const { container } = render(<EnginePanel {...defaultProps} />);

      const panels = container.querySelectorAll('.command-panel');
      expect(panels.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Loading States', () => {
    it('should pass loading prop to TurnPipelineStatus', () => {
      render(<EnginePanel {...defaultProps} loading={true} />);

      const pipelineStatus = screen.getByTestId('turn-pipeline-status');
      expect(pipelineStatus).toHaveAttribute('data-loading', 'true');
    });

    it('should pass loading prop to RealTimeActivity', () => {
      render(<EnginePanel {...defaultProps} loading={true} />);

      const activity = screen.getByTestId('real-time-activity');
      expect(activity).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('Error States', () => {
    it('should pass error prop to TurnPipelineStatus', () => {
      render(<EnginePanel {...defaultProps} error={true} />);

      const pipelineStatus = screen.getByTestId('turn-pipeline-status');
      expect(pipelineStatus).toHaveAttribute('data-error', 'true');
    });

    it('should pass error prop to RealTimeActivity', () => {
      render(<EnginePanel {...defaultProps} error={true} />);

      const activity = screen.getByTestId('real-time-activity');
      expect(activity).toHaveAttribute('data-error', 'true');
    });
  });

  describe('Pipeline Status', () => {
    it('should pass pipelineStatus to TurnPipelineStatus', () => {
      render(<EnginePanel {...defaultProps} pipelineStatus="running" />);

      const pipelineStatus = screen.getByTestId('turn-pipeline-status');
      expect(pipelineStatus).toHaveAttribute('data-status', 'running');
    });

    it('should pass isLive to TurnPipelineStatus', () => {
      render(<EnginePanel {...defaultProps} isLive={true} />);

      const pipelineStatus = screen.getByTestId('turn-pipeline-status');
      expect(pipelineStatus).toHaveAttribute('data-live', 'true');
    });
  });

  describe('Close Button', () => {
    it('should render close button when onClose provided', () => {
      const onClose = vi.fn();
      render(<EnginePanel {...defaultProps} onClose={onClose} />);

      const closeButton = screen.getByRole('button', { name: /close.*panel/i });
      expect(closeButton).toBeInTheDocument();
    });

    it('should not render close button when onClose not provided', () => {
      render(<EnginePanel {...defaultProps} />);

      const closeButton = screen.queryByRole('button', { name: /close.*panel/i });
      expect(closeButton).not.toBeInTheDocument();
    });

    it('should call onClose when close button clicked', () => {
      const onClose = vi.fn();
      render(<EnginePanel {...defaultProps} onClose={onClose} />);

      const closeButton = screen.getByRole('button', { name: /close.*panel/i });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('RealTimeActivity Configuration', () => {
    it('should pass condensed density to RealTimeActivity', () => {
      render(<EnginePanel {...defaultProps} />);

      const activity = screen.getByTestId('real-time-activity');
      expect(activity).toHaveAttribute('data-density', 'condensed');
    });
  });
});
