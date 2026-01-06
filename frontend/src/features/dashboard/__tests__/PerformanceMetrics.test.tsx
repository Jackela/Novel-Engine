import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import PerformanceMetrics from '../PerformanceMetrics';

// Mock usePerformance
vi.mock('../../../hooks/usePerformance', () => ({
  usePerformance: vi.fn(() => ({
    trackWebVitals: vi.fn(),
    reportMetric: vi.fn(),
    getRenderCount: vi.fn(() => 1),
    measureInteraction: vi.fn(),
  })),
}));

const env = import.meta.env as ImportMetaEnv & {
  VITE_SHOW_PERFORMANCE_METRICS?: string;
};

const setMetricsEnv = (value: string | undefined) => {
  if (value === undefined) {
    delete env.VITE_SHOW_PERFORMANCE_METRICS;
    return;
  }
  env.VITE_SHOW_PERFORMANCE_METRICS = value;
};

describe('PerformanceMetrics RBAC', () => {
  let originalEnv: string | undefined;

  beforeEach(() => {
    vi.clearAllMocks();
    originalEnv = import.meta.env.VITE_SHOW_PERFORMANCE_METRICS;
    setMetricsEnv('true');
  });

  afterEach(() => {
    setMetricsEnv(originalEnv);
  });

  it('renders when env var is set (RBAC fallback)', () => {
    setMetricsEnv('true');

    render(<PerformanceMetrics />);
    expect(screen.getByText(/Core Web Vitals/i)).toBeInTheDocument();
  });

  it('hidden when env var is not set', () => {
    setMetricsEnv('false');

    const { container } = render(<PerformanceMetrics />);
    expect(screen.queryByText(/Core Web Vitals/i)).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });

  it('hidden when env var is undefined', () => {
    setMetricsEnv(undefined);

    const { container } = render(<PerformanceMetrics />);
    expect(screen.queryByText(/Core Web Vitals/i)).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });
});

describe('PerformanceMetrics content', () => {
  beforeEach(() => {
    setMetricsEnv('true');
  });

  afterEach(() => {
    setMetricsEnv(undefined);
  });

  it('displays Core Web Vitals label', () => {
    render(<PerformanceMetrics />);
    expect(screen.getByText(/Core Web Vitals/i)).toBeInTheDocument();
  });

  it('displays all five Web Vitals metrics', () => {
    render(<PerformanceMetrics />);

    expect(screen.getByText(/LCP/i)).toBeInTheDocument();
    expect(screen.getByText(/FID/i)).toBeInTheDocument();
    expect(screen.getByText(/CLS/i)).toBeInTheDocument();
    expect(screen.getByText(/FCP/i)).toBeInTheDocument();
    expect(screen.getByText(/TTFB/i)).toBeInTheDocument();
  });

  it('does not display demo metrics (responseTime, errorRate, etc.)', () => {
    render(<PerformanceMetrics />);

    expect(screen.queryByText(/Response/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Error Rate/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Memory/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Load/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/RPS/i)).not.toBeInTheDocument();
  });
});

describe('PerformanceMetrics RBAC fallback notes', () => {
  beforeEach(() => {
    setMetricsEnv('true');
  });

  afterEach(() => {
    setMetricsEnv(undefined);
  });

  it('renders for developer role (RBAC integration note)', () => {
    render(<PerformanceMetrics />);
    expect(screen.getByText(/Core Web Vitals/i)).toBeInTheDocument();
  });

  it('renders for admin role (RBAC integration note)', () => {
    render(<PerformanceMetrics />);
    expect(screen.getByText(/Core Web Vitals/i)).toBeInTheDocument();
  });

  it('renders for user with multiple roles including developer (RBAC integration note)', () => {
    render(<PerformanceMetrics />);
    expect(screen.getByText(/Core Web Vitals/i)).toBeInTheDocument();
  });

  it('hidden for regular user (RBAC integration note)', () => {
    setMetricsEnv('false');

    const { container } = render(<PerformanceMetrics />);
    expect(screen.queryByText(/Performance Metrics/i)).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });
});
