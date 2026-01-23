import { useCallback } from 'react';

type VirtualScrollConfig = {
  itemCount: number;
  itemSize: number;
  height: number;
  overscan: number;
};

const runDeferred = (callback: () => void) => {
  const globalRef = globalThis as typeof globalThis & {
    requestIdleCallback?: (cb: () => void) => number;
  };

  if (globalRef.requestIdleCallback) {
    globalRef.requestIdleCallback(callback);
  } else if (typeof globalRef.setTimeout === 'function') {
    globalRef.setTimeout(callback, 0);
  } else {
    callback();
  }
};

export const usePerformanceOptimizer = () => {
  const deferUpdate = useCallback((callback: () => void) => {
    runDeferred(callback);
  }, []);

  const measureInteractionDelay = useCallback((callback: () => void) => {
    const start = typeof performance === 'undefined' ? 0 : performance.now();
    callback();
    const end = typeof performance === 'undefined' ? 0 : performance.now();
    return end - start;
  }, []);

  const createVirtualScrollConfig = useCallback(
    (
      itemCount: number,
      itemSize: number,
      height: number,
      overscan = 6
    ): VirtualScrollConfig => ({
      itemCount,
      itemSize,
      height,
      overscan,
    }),
    []
  );

  const optimizeForRealTime = useCallback(() => {
    // Placeholder for adaptive performance tuning hooks
  }, []);

  return {
    deferUpdate,
    measureInteractionDelay,
    createVirtualScrollConfig,
    optimizeForRealTime,
  };
};
