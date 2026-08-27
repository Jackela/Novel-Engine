import { getByRole, queryByRole } from '@testing-library/dom';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { WholeBookPhase } from '../hooks/useWholeBookLoop';

import { StudioWholeBookControl } from './StudioWholeBookControl';

const mountedContainers: Array<{ container: HTMLDivElement; root: ReturnType<typeof createRoot> }> =
  [];

afterEach(() => {
  for (const { container, root } of mountedContainers) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedContainers.length = 0;
});

function render(phase: WholeBookPhase, remaining = 3): HTMLDivElement {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedContainers.push({ container, root });
  act(() => {
    root.render(
      <StudioWholeBookControl
        phase={phase}
        remaining={remaining}
        onStart={vi.fn()}
        onStop={vi.fn()}
      />,
    );
  });
  return container;
}

describe('StudioWholeBookControl (#318)', () => {
  it('offers the start control while idle and reports the pending count', () => {
    const container = render({ kind: 'idle' }, 2);
    const start = getByRole(container, 'button', { name: /Generate whole book/i });
    expect(start).toBeEnabled();
    expect(queryByRole(container, 'button', { name: /Stop generating/i })).toBeNull();
  });

  it('disables start when every chapter already has an accepted AI revision', () => {
    const container = render({ kind: 'idle' }, 0);
    expect(getByRole(container, 'button', { name: /Generate whole book/i })).toBeDisabled();
  });

  it('shows progress and the stop control while running', () => {
    const container = render({ kind: 'running', current: 2, total: 5 });
    expect(container.querySelector('[role="status"]')?.textContent).toContain(
      'Generating chapter 2 of 5',
    );
    expect(getByRole(container, 'button', { name: /Stop generating/i })).toBeInTheDocument();
    expect(queryByRole(container, 'button', { name: /Generate whole book/i })).toBeNull();
  });

  it('reports how much work a stopped run preserved', () => {
    const container = render({ kind: 'done', generated: 2, stoppedEarly: true });
    expect(container.querySelector('.whole-book__outcome')?.textContent).toContain(
      'Stopped — 2 chapters accepted this run',
    );
  });

  it('surfaces a failed chapter through the alert role', () => {
    const container = render({
      kind: 'failed',
      generated: 1,
      failedChapterTitle: 'Chapter Two',
      message: 'Provider exploded.',
    });
    const failure = getByRole(container, 'alert');
    expect(failure.textContent).toContain('Failed on “Chapter Two”');
    expect(failure.textContent).toContain('Provider exploded.');
  });
});
