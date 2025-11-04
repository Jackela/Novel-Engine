import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import GenerationProgress from './GenerationProgress';

/**
 * Regression test suite for GenerationProgress component
 * Ensures backward compatibility with original props interface
 */

describe('GenerationProgress - Backward Compatibility', () => {
  const defaultProps = {
    isGenerating: true,
    progress: 50,
    currentStage: 'generating',
    estimatedTimeRemaining: 60,
    error: null,
  };

  test('renders with original props only (no WebSocket props)', () => {
    render(<GenerationProgress {...defaultProps} />);
    
    // Should display basic progress information
    expect(screen.getByText('Generating Story...')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText(/1m 0s remaining/)).toBeInTheDocument();
  });

  test('handles progress without WebSocket features', () => {
    render(
      <GenerationProgress
        {...defaultProps}
        progress={75}
        currentStage="finalizing"
        estimatedTimeRemaining={30}
      />
    );
    
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText(/30s remaining/)).toBeInTheDocument();
  });

  test('displays error state correctly', () => {
    render(
      <GenerationProgress
        {...defaultProps}
        error="Generation failed: Network error"
        isGenerating={false}
      />
    );
    
    expect(screen.getByText('Generation Failed')).toBeInTheDocument();
    expect(screen.getByText('Generation failed: Network error')).toBeInTheDocument();
  });

  test('shows completion state without WebSocket', () => {
    render(
      <GenerationProgress
        {...defaultProps}
        isGenerating={false}
        progress={100}
        currentStage="completed"
      />
    );
    
    expect(screen.getByText('Story Generation Complete')).toBeInTheDocument();
  });

  test('WebSocket features are disabled by default', () => {
    render(<GenerationProgress {...defaultProps} />);
    
    // Should not show WebSocket connection indicators
    expect(screen.queryByTestId('websocket-indicator')).not.toBeInTheDocument();
    expect(screen.queryByText('Real-time updates active')).not.toBeInTheDocument();
  });

  test('gracefully handles undefined optional props', () => {
    render(
      <GenerationProgress
        {...defaultProps}
        generationId={undefined}
        enableRealTimeUpdates={undefined}
      />
    );
    
    // Should render without errors
    expect(screen.getByText('Generating Story...')).toBeInTheDocument();
  });

  test('WebSocket features only activate when explicitly enabled', () => {
    render(
      <GenerationProgress
        {...defaultProps}
        generationId="test-123"
        enableRealTimeUpdates={false}
      />
    );
    
    // WebSocket should be disabled even with generation ID
    expect(screen.queryByTestId('websocket-indicator')).not.toBeInTheDocument();
  });

  test('maintains existing stage progression logic', () => {
    const { rerender } = render(
      <GenerationProgress
        {...defaultProps}
        progress={25}
        currentStage="analyzing"
      />
    );
    
    expect(screen.getAllByText(/Character Analysis/)[0]).toBeInTheDocument();
    
    rerender(
      <GenerationProgress
        {...defaultProps}
        progress={75}
        currentStage="generating"
      />
    );
    
    expect(screen.getByText(/Story Generation/)).toBeInTheDocument();
  });

  test('preserves original performance metrics display', () => {
    render(<GenerationProgress {...defaultProps} />);
    
    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    expect(screen.getByText('Est. Total Time')).toBeInTheDocument();
    expect(screen.getByText('Turns Processed')).toBeInTheDocument();
    expect(screen.getByText('Multi-Agent')).toBeInTheDocument();
  });

  test('maintains original "What\'s Happening?" section', () => {
    render(<GenerationProgress {...defaultProps} />);
    
    expect(screen.getByText("What's Happening?")).toBeInTheDocument();
    expect(screen.getAllByText(/Character Analysis/)[0]).toBeInTheDocument();
    expect(screen.getByText(/Narrative Planning/)).toBeInTheDocument();
    expect(screen.getByText(/Turn Generation/)).toBeInTheDocument();
    expect(screen.getByText(/Quality Control/)).toBeInTheDocument();
  });
});

/**
 * Integration test for StoryWorkshop component usage
 */
describe('GenerationProgress - StoryWorkshop Integration', () => {
  test('accepts props from StoryWorkshop without issues', () => {
    // Simulate how StoryWorkshop passes props
    const storyWorkshopProps = {
      isGenerating: true,
      progress: 45,
      currentStage: 'Coordinating character interactions...',
      estimatedTimeRemaining: 90,
      error: null,
      generationId: 'story_abc123',
      enableRealTimeUpdates: true,
    };
    
    render(<GenerationProgress {...storyWorkshopProps} />);
    
    expect(screen.getByText('Generating Story...')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });
});