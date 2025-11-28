/**
 * WorldPanel Component Tests
 *
 * Tests cover:
 * 1. Structure and rendering
 * 2. Expand button functionality
 * 3. Loading and error state propagation
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock WorldStateMapV2 to avoid complex dependencies
vi.mock('@/components/dashboard/WorldStateMapV2', () => ({
  default: ({ loading, error }: { loading: boolean; error: boolean }) => (
    <div data-testid="world-state-map" data-loading={loading} data-error={error}>
      World State Map Mock
    </div>
  ),
}));

import WorldPanel from '@/components/dashboard/panels/WorldPanel';

describe('WorldPanel', () => {
  describe('Structure', () => {
    it('should render WorldStateMap component', () => {
      render(<WorldPanel loading={false} error={false} />);

      expect(screen.getByTestId('world-state-map')).toBeInTheDocument();
    });

    it('should have command-panel class on container', () => {
      const { container } = render(<WorldPanel loading={false} error={false} />);

      expect(container.querySelector('.command-panel')).toBeInTheDocument();
    });
  });

  describe('Expand Button', () => {
    it('should render expand button when onExpand provided', () => {
      const onExpand = vi.fn();
      render(<WorldPanel loading={false} error={false} onExpand={onExpand} />);

      expect(screen.getByRole('button', { name: /expand/i })).toBeInTheDocument();
    });

    it('should not render expand button when onExpand not provided', () => {
      render(<WorldPanel loading={false} error={false} />);

      expect(screen.queryByRole('button', { name: /expand/i })).not.toBeInTheDocument();
    });

    it('should call onExpand when expand button clicked', () => {
      const onExpand = vi.fn();
      render(<WorldPanel loading={false} error={false} onExpand={onExpand} />);

      const expandButton = screen.getByRole('button', { name: /expand/i });
      fireEvent.click(expandButton);

      expect(onExpand).toHaveBeenCalledTimes(1);
    });
  });

  describe('Loading and Error States', () => {
    it('should pass loading prop to WorldStateMap', () => {
      render(<WorldPanel loading={true} error={false} />);

      const map = screen.getByTestId('world-state-map');
      expect(map).toHaveAttribute('data-loading', 'true');
    });

    it('should pass error prop to WorldStateMap', () => {
      render(<WorldPanel loading={false} error={true} />);

      const map = screen.getByTestId('world-state-map');
      expect(map).toHaveAttribute('data-error', 'true');
    });

    it('should pass both loading and error props correctly', () => {
      render(<WorldPanel loading={true} error={true} />);

      const map = screen.getByTestId('world-state-map');
      expect(map).toHaveAttribute('data-loading', 'true');
      expect(map).toHaveAttribute('data-error', 'true');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label on expand button', () => {
      const onExpand = vi.fn();
      render(<WorldPanel loading={false} error={false} onExpand={onExpand} />);

      const expandButton = screen.getByRole('button', { name: /expand/i });
      expect(expandButton).toHaveAttribute('aria-label', 'Expand world map');
    });
  });
});
