import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { act } from 'react';
import React from 'react';
import OnboardingWizard from '../../src/components/OnboardingWizard';

// Mock WizardNavigation (component + hook) to provide simple Next navigation
vi.mock('../../src/components/WizardNavigation', () => {
  const React = require('react');
  const useWizardNavigation = (_start: number, total: number) => {
    // Force start at 'demo' (index 3) to bypass earlier steps
    const [currentStep, setCurrentStep] = React.useState(3);
    const [completedSteps, setCompleted] = React.useState<number[]>([]);
    const [navigationHistory, setHistory] = React.useState<number[]>([3]);
    return {
      currentStep,
      completedSteps,
      navigationHistory,
      goToStep: (n: number) => { setCurrentStep(n); setHistory((h: number[]) => [...h, n]); },
      goNext: () => setCurrentStep((i: number) => Math.min(i + 1, total - 1)),
      goPrev: () => setCurrentStep((i: number) => Math.max(i - 1, 0)),
      markStepCompleted: (n: number) => setCompleted((arr: number[]) => arr.includes(n) ? arr : [...arr, n]),
    };
  };
  const WizardNav = (props: any) => (
    <div className="wizard-navigation">
      <button aria-label="Wizard Next" onClick={() => props.onStepChange(props.currentStep + 1, 'next')}>Wizard Next</button>
    </div>
  );
  return { __esModule: true, default: WizardNav, useWizardNavigation };
});

// Make WizardStep a transparent wrapper to avoid layout gating in tests
vi.mock('../../src/components/WizardStep', () => ({
  __esModule: true,
  default: (props: any) => <div data-testid="wizard-step">{props.children}<button aria-label="Step Next">Step Next</button></div>,
}));

// Progress tracker can trigger additional updates; mock to noop for stability
vi.mock('../../src/components/ProgressTracker', () => ({
  __esModule: true,
  default: () => null,
}));

// Minimal mocks to stabilize environment-dependent hooks used by the wizard
vi.mock('../../src/components/utils/PortDetector', () => ({
  usePortDetection: () => ({
    config: { baseUrl: 'http://localhost:8000' },
    isDetecting: false,
    detectConfig: vi.fn(),
    getApiUrl: () => 'http://localhost:8000'
  })
}));

// Some code paths may import a non-component utils version; mock it too
vi.mock('../../src/utils/PortDetector', () => ({
  usePortDetection: () => ({
    config: { baseUrl: 'http://localhost:8000' },
    isDetecting: false,
    detectConfig: vi.fn(),
    getApiUrl: () => 'http://localhost:8000'
  }),
  detectBackendConfig: vi.fn(async () => ({ baseUrl: 'http://localhost:8000' })),
  healthCheck: vi.fn(async () => ({ api: 'healthy', config: 'loaded', version: '1.0.0' })),
}));

vi.mock('../../src/components/utils/HealthMonitor', () => ({
  useHealthMonitor: () => ({
    healthData: { overall: { level: 'good' } },
    startMonitoring: vi.fn()
  })
}));

vi.mock('../../src/components/utils/EnvironmentValidator', () => ({
  useEnvironmentValidator: () => ({
    validationData: { overall: { level: 'pass' } },
    validateEnvironment: vi.fn()
  })
}));

// NOTE: This test exercises wizard wiring with mocked navigation and env hooks.
// It can be enabled after stabilizing PortDetector/validators to avoid timeouts.
describe('OnboardingWizard + DemoStep integration', () => {
  it('navigates to demo step, generates a story, and advances', async () => {
    const onComplete = vi.fn();
    const { container } = render(<OnboardingWizard onComplete={onComplete} allowSkip showProgress={false} theme="gradient" />);

    // Mock starts at Demo step via useWizardNavigation mock

    // In DemoStep: pick first story and generate
    // Wait for grid to appear to avoid race with initial render
    let grid: Element | null = null;
    for (let i = 0; i < 10; i++) {
      grid = container.querySelector('.story-grid');
      if (grid) break;
      // yield to microtask queue
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, 0));
    }
    expect(grid).toBeTruthy();
    await act(async () => {
      fireEvent.click((grid as Element).querySelector('.story-card') as HTMLElement);
    });

    const generateBtn = await screen.findByRole('button', { name: /generate/i });
    (vi as any).useFakeTimers?.();
    await act(async () => {
      fireEvent.click(generateBtn);
      (vi as any).advanceTimersByTime?.(2100);
    });

    // Preview appears; mark step as done by clicking Next to move to completion
    expect(await screen.findByText(/preview/i)).toBeTruthy();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /wizard next/i })); // demo -> completion
    });

    expect(await screen.findByText(/setup complete/i)).toBeTruthy();
  });
});
