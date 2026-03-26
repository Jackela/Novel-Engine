import type { ReactElement } from 'react';
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import {
  fireEvent,
  screen,
  waitFor,
  within,
} from '@testing-library/dom';

type RenderOptions = {
  container?: HTMLElement;
  baseElement?: HTMLElement;
};

type RenderResult = ReturnType<typeof within> & {
  container: HTMLElement;
  baseElement: HTMLElement;
  rerender: (ui: ReactElement) => void;
  unmount: () => void;
};

const mountedRoots = new Map<HTMLElement, Root>();

function attachContainer(container: HTMLElement, baseElement: HTMLElement): void {
  if (!container.isConnected) {
    baseElement.append(container);
  }
}

function detachContainer(container: HTMLElement): void {
  if (container.isConnected) {
    container.remove();
  }
}

function unmountContainer(container: HTMLElement): void {
  const root = mountedRoots.get(container);

  if (!root) {
    detachContainer(container);
    return;
  }

  act(() => {
    root.unmount();
  });

  mountedRoots.delete(container);
  detachContainer(container);
}

export function cleanup(): void {
  for (const container of Array.from(mountedRoots.keys())) {
    unmountContainer(container);
  }

  document.body.replaceChildren();
}

export function render(
  ui: ReactElement,
  options: RenderOptions = {},
): RenderResult {
  const container = options.container ?? document.createElement('div');
  const baseElement = options.baseElement ?? document.body;

  attachContainer(container, baseElement);

  const root = createRoot(container);
  mountedRoots.set(container, root);

  act(() => {
    root.render(ui);
  });

  return {
    ...within(container),
    container,
    baseElement,
    rerender(nextUi: ReactElement) {
      act(() => {
        root.render(nextUi);
      });
    },
    unmount() {
      unmountContainer(container);
    },
  };
}

export { fireEvent, screen, waitFor, within };
