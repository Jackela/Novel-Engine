import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import React from 'react';
import DemoStep from '../../src/components/steps/DemoStep';

describe('DemoStep', () => {
  it('renders, selects a story, generates preview, and calls onStoryGenerated', async () => {
    const onStoryGenerated = vi.fn();
    const { container } = render(
      <DemoStep hasApiKey={false} onStoryGenerated={onStoryGenerated} />
    );

    // Select first story card
    const grid = container.querySelector('.story-grid');
    expect(grid).toBeTruthy();
    const firstCard = grid!.querySelector('.story-card') as HTMLElement;
    expect(firstCard).toBeTruthy();
    fireEvent.click(firstCard);

    // Click generate button
    const generateBtn = await screen.findByRole('button', { name: /generate/i });
    // Speed up timer-driven generation
    const useFakeTimers = (globalThis as any).vi?.useFakeTimers;
    if (useFakeTimers) (vi as any).useFakeTimers();
    fireEvent.click(generateBtn);
    if (useFakeTimers) (vi as any).advanceTimersByTime(2100);

    // Preview should appear and callback should be called
    const preview = await screen.findByText(/preview/i);
    expect(preview).toBeTruthy();
    expect(onStoryGenerated).toHaveBeenCalled();

    // Restore timers
    const useRealTimers = (globalThis as any).vi?.useRealTimers;
    if (useRealTimers) (vi as any).useRealTimers();
  });
});

