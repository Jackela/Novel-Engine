import { act, type ReactElement } from "react";
import { createRoot, type Root } from "react-dom/client";

/**
 * Shared React test harness (#410): mount/cleanup bookkeeping for
 * `createRoot`-based hook and component tests plus the deferred-promise
 * pattern. Mock resets stay in each test file's own `afterEach` because
 * files differ in timer/global stubbing needs.
 */

export interface MountedRoot {
  readonly container: HTMLDivElement;
  readonly root: Root;
}

export interface Deferred<T> {
  readonly promise: Promise<T>;
  resolve: (value: T) => void;
}

export function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolveValue) => {
    resolve = resolveValue;
  });
  return { promise, resolve };
}

export function createMountHarness(): {
  readonly mount: (element: ReactElement) => MountedRoot;
  readonly unmount: (container: HTMLDivElement) => void;
  readonly cleanup: () => void;
} {
  const mountedRoots: MountedRoot[] = [];

  function mount(element: ReactElement): MountedRoot {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    mountedRoots.push({ container, root });
    act(() => {
      root.render(element);
    });
    return { container, root };
  }

  /** Unmount one root early and keep `cleanup` from unmounting it twice. */
  function unmount(container: HTMLDivElement): void {
    const index = mountedRoots.findIndex((entry) => entry.container === container);
    if (index >= 0) {
      const [{ root }] = mountedRoots.splice(index, 1);
      act(() => {
        root.unmount();
      });
      container.remove();
    }
  }

  function cleanup(): void {
    for (const { container, root } of mountedRoots) {
      act(() => {
        root.unmount();
      });
      container.remove();
    }
    mountedRoots.length = 0;
  }

  return { mount, unmount, cleanup };
}

/** Let one microtask tick run inside `act` (single await). */
export async function flushMicrotasks(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

/** Let chained effect continuations settle inside `act` (double await). */
export async function flushEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}
