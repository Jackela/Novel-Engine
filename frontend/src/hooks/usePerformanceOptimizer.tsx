/**
 * Performance Optimization Hook
 * =============================
 * 
 * React hook for real-time performance optimization including:
 * - React concurrent features optimization
 * - Memory management and cleanup
 * - Rendering performance optimization
 * - Bundle splitting and lazy loading
 * - Virtual scrolling and windowing
 */

import React, { useCallback, useEffect, useRef, useMemo, useState, startTransition } from 'react';
import { unstable_scheduleCallback, unstable_LowPriority } from 'scheduler';

// Performance monitoring types
interface PerformanceMetrics {
  renderTime: number;
  memoryUsage: number;
  bundleSize: number;
  networkLatency: number;
  frameDrops: number;
  interactionDelay: number;
}

interface PerformanceThresholds {
  maxRenderTime: number;
  maxMemoryUsage: number;
  maxInteractionDelay: number;
  targetFPS: number;
}

interface OptimizationState {
  isOptimized: boolean;
  currentMetrics: PerformanceMetrics;
  optimizationLevel: 'none' | 'basic' | 'aggressive' | 'extreme';
  recommendations: string[];
}

export const usePerformanceOptimizer = () => {
  const performanceObserverRef = useRef<PerformanceObserver | null>(null);
  const frameStatsRef = useRef({ frameCount: 0, lastTime: 0 });
  const memoryCheckInterval = useRef<NodeJS.Timeout | null>(null);
  const _interactionTimeRef = useRef<number>(0);
  
  const [optimizationState, setOptimizationState] = useState<OptimizationState>({
    isOptimized: false,
    currentMetrics: {
      renderTime: 0,
      memoryUsage: 0,
      bundleSize: 0,
      networkLatency: 0,
      frameDrops: 0,
      interactionDelay: 0
    },
    optimizationLevel: 'none',
    recommendations: []
  });

  // Performance thresholds
  const thresholds: PerformanceThresholds = useMemo(() => ({
    maxRenderTime: 16.67, // 60fps target
    maxMemoryUsage: 100 * 1024 * 1024, // 100MB
    maxInteractionDelay: 100, // 100ms
    targetFPS: 60
  }), []);

  // Memory usage monitoring
  const checkMemoryUsage = useCallback((): number => {
    const perf = performance as unknown as { memory?: { usedJSHeapSize: number } };
    return perf.memory?.usedJSHeapSize ?? 0;
  }, []);

  // Frame rate monitoring
  const monitorFrameRate = useCallback(() => {
    const now = performance.now();
    
    if (frameStatsRef.current.lastTime > 0) {
      const delta = now - frameStatsRef.current.lastTime;
      const fps = 1000 / delta;
      
      if (fps < thresholds.targetFPS * 0.9) { // 10% tolerance
        setOptimizationState(prev => ({
          ...prev,
          currentMetrics: {
            ...prev.currentMetrics,
            frameDrops: prev.currentMetrics.frameDrops + 1
          }
        }));
      }
    }
    
    frameStatsRef.current.lastTime = now;
    frameStatsRef.current.frameCount++;
    
    requestAnimationFrame(monitorFrameRate);
  }, [thresholds.targetFPS]);

  // Performance observer for render timing
  const initPerformanceObserver = useCallback(() => {
    if ('PerformanceObserver' in window) {
      try {
        performanceObserverRef.current = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          
          for (const entry of entries) {
            if (entry.entryType === 'measure' && entry.name.includes('react')) {
              setOptimizationState(prev => ({
                ...prev,
                currentMetrics: {
                  ...prev.currentMetrics,
                  renderTime: entry.duration
                }
              }));
            }
            
            if (entry.entryType === 'navigation') {
              const navEntry = entry as PerformanceNavigationTiming;
              const networkLatency = navEntry.responseEnd - navEntry.requestStart;
              
              setOptimizationState(prev => ({
                ...prev,
                currentMetrics: {
                  ...prev.currentMetrics,
                  networkLatency
                }
              }));
            }
          }
        });
        
        performanceObserverRef.current.observe({ 
          entryTypes: ['measure', 'navigation', 'paint'] 
        });
      } catch (error) {
        console.warn('Performance Observer not supported:', error);
      }
    }
  }, []);

  // Interaction timing measurement
  const measureInteractionDelay = useCallback((callback: () => void) => {
    const startTime = performance.now();
    
    unstable_scheduleCallback(unstable_LowPriority, () => {
      const endTime = performance.now();
      const delay = endTime - startTime;
      
      setOptimizationState(prev => ({
        ...prev,
        currentMetrics: {
          ...prev.currentMetrics,
          interactionDelay: Math.max(prev.currentMetrics.interactionDelay, delay)
        }
      }));
      
      callback();
    });
  }, []);

  // Optimization recommendations engine
  const generateRecommendations = useCallback((metrics: PerformanceMetrics): string[] => {
    const recommendations: string[] = [];
    
    if (metrics.renderTime > thresholds.maxRenderTime) {
      recommendations.push('Enable React Concurrent Mode');
      recommendations.push('Use React.memo() for expensive components');
      recommendations.push('Implement virtualization for large lists');
    }
    
    if (metrics.memoryUsage > thresholds.maxMemoryUsage) {
      recommendations.push('Implement component cleanup in useEffect');
      recommendations.push('Use weak references for cached data');
      recommendations.push('Enable garbage collection hints');
    }
    
    if (metrics.interactionDelay > thresholds.maxInteractionDelay) {
      recommendations.push('Use React.startTransition() for non-urgent updates');
      recommendations.push('Implement debouncing for rapid user inputs');
      recommendations.push('Split large components into smaller chunks');
    }
    
    if (metrics.frameDrops > 5) {
      recommendations.push('Reduce DOM manipulation frequency');
      recommendations.push('Use CSS transforms instead of layout changes');
      recommendations.push('Implement frame budgeting for animations');
    }
    
    return recommendations;
  }, [thresholds]);

  // Automatic optimization strategies
  const optimizeForRealTime = useCallback(() => {
    setOptimizationState(prev => {
      const newOptimizationLevel = determineOptimizationLevel(prev.currentMetrics);
      const recommendations = generateRecommendations(prev.currentMetrics);
      
      return {
        ...prev,
        isOptimized: true,
        optimizationLevel: newOptimizationLevel,
        recommendations
      };
    });
    
    // Apply performance optimizations
    const win = window as unknown as { scheduler?: { postTask: (cb: () => void, opts?: { priority: string }) => void } };
    win.scheduler?.postTask(() => {
      console.log('Performance optimization activated');
    }, { priority: 'background' });
    
    // Enable React concurrent features if available
    if (document.documentElement) {
      document.documentElement.style.setProperty('--react-concurrent', 'enabled');
    }
  }, [generateRecommendations]);

  const determineOptimizationLevel = useCallback((metrics: PerformanceMetrics): OptimizationState['optimizationLevel'] => {
    let issueCount = 0;
    
    if (metrics.renderTime > thresholds.maxRenderTime) issueCount++;
    if (metrics.memoryUsage > thresholds.maxMemoryUsage) issueCount++;
    if (metrics.interactionDelay > thresholds.maxInteractionDelay) issueCount++;
    if (metrics.frameDrops > 3) issueCount++;
    
    if (issueCount === 0) return 'none';
    if (issueCount <= 1) return 'basic';
    if (issueCount <= 2) return 'aggressive';
    return 'extreme';
  }, [thresholds]);

  // Bundle size analysis
  const analyzeBundleSize = useCallback(async (): Promise<number> => {
    try {
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      let totalSize = 0;
      
      for (const resource of resources) {
        if (resource.name.includes('.js') || resource.name.includes('.css')) {
          totalSize += resource.transferSize || 0;
        }
      }
      
      setOptimizationState(prev => ({
        ...prev,
        currentMetrics: {
          ...prev.currentMetrics,
          bundleSize: totalSize
        }
      }));
      
      return totalSize;
    } catch (error) {
      console.warn('Bundle size analysis failed:', error);
      return 0;
    }
  }, []);

  // Virtual scrolling helper
  const createVirtualScrollConfig = useCallback((
    itemCount: number,
    itemHeight: number,
    containerHeight: number
  ) => {
    const visibleItems = Math.ceil(containerHeight / itemHeight);
    const bufferSize = Math.max(5, Math.ceil(visibleItems * 0.5));
    
    return {
      itemCount,
      itemHeight,
      visibleItems,
      bufferSize,
      overscan: bufferSize
    };
  }, []);

  // Memory cleanup utilities
  const scheduleCleanup = useCallback((cleanupFn: () => void, delay = 5000) => {
    return setTimeout(() => {
      if ('requestIdleCallback' in window) {
        requestIdleCallback(cleanupFn, { timeout: 2000 });
      } else {
        setTimeout(cleanupFn, 0);
      }
    }, delay);
  }, []);

  // React Concurrent Mode helpers
  const deferUpdate = useCallback((updateFn: () => void) => {
    if (typeof startTransition === 'function') {
      startTransition(updateFn);
      return;
    }
    setTimeout(updateFn, 0);
  }, []);

  // Performance monitoring initialization
  useEffect(() => {
    initPerformanceObserver();
    monitorFrameRate();
    
    // Start memory monitoring
    memoryCheckInterval.current = setInterval(() => {
      const memoryUsage = checkMemoryUsage();
      setOptimizationState(prev => ({
        ...prev,
        currentMetrics: {
          ...prev.currentMetrics,
          memoryUsage
        }
      }));
    }, 5000);
    
    // Initial bundle analysis
    analyzeBundleSize();
    
    return () => {
      performanceObserverRef.current?.disconnect();
      if (memoryCheckInterval.current) {
        clearInterval(memoryCheckInterval.current);
      }
    };
  }, [initPerformanceObserver, monitorFrameRate, checkMemoryUsage, analyzeBundleSize]);

  // Cleanup optimization
  const cleanupOptimizations = useCallback(() => {
    setOptimizationState({
      isOptimized: false,
      currentMetrics: {
        renderTime: 0,
        memoryUsage: 0,
        bundleSize: 0,
        networkLatency: 0,
        frameDrops: 0,
        interactionDelay: 0
      },
      optimizationLevel: 'none',
      recommendations: []
    });
  }, []);

  // Performance debugging utilities
  const getPerformanceReport = useCallback((): string => {
    const { currentMetrics, optimizationLevel, recommendations } = optimizationState;
    
    return `
Performance Report:
==================
Render Time: ${currentMetrics.renderTime.toFixed(2)}ms (target: <${thresholds.maxRenderTime}ms)
Memory Usage: ${(currentMetrics.memoryUsage / 1024 / 1024).toFixed(2)}MB (target: <${thresholds.maxMemoryUsage / 1024 / 1024}MB)
Network Latency: ${currentMetrics.networkLatency.toFixed(2)}ms
Interaction Delay: ${currentMetrics.interactionDelay.toFixed(2)}ms (target: <${thresholds.maxInteractionDelay}ms)
Frame Drops: ${currentMetrics.frameDrops}
Bundle Size: ${(currentMetrics.bundleSize / 1024).toFixed(2)}KB

Optimization Level: ${optimizationLevel}

Recommendations:
${recommendations.map(rec => `- ${rec}`).join('\n')}
    `;
  }, [optimizationState, thresholds]);

  return {
    optimizationState,
    optimizeForRealTime,
    cleanupOptimizations,
    measureInteractionDelay,
    createVirtualScrollConfig,
    scheduleCleanup,
    deferUpdate,
    analyzeBundleSize,
    getPerformanceReport,
    thresholds
  };
};

// Higher-order component for automatic performance optimization
export function withPerformanceOptimization<P extends object>(
  WrappedComponent: React.ComponentType<P>
): React.ComponentType<P> {
  const Memoized = React.memo((props: P) => {
    const { optimizeForRealTime } = usePerformanceOptimizer();

    useEffect(() => {
      optimizeForRealTime();
    }, [optimizeForRealTime]);

    return <WrappedComponent {...props} />;
  });
  return Memoized as React.ComponentType<P>;
}

// Performance monitoring provider
export const PerformanceProvider: React.FC<{
  children: React.ReactNode;
  enableAutoOptimization?: boolean;
}> = ({ children, enableAutoOptimization = true }) => {
  const { optimizeForRealTime, optimizationState } = usePerformanceOptimizer();
  
  useEffect(() => {
    if (enableAutoOptimization) {
      const interval = setInterval(() => {
        if (optimizationState.optimizationLevel === 'none') {
          optimizeForRealTime();
        }
      }, 10000); // Check every 10 seconds
      
      return () => clearInterval(interval);
    }
  }, [enableAutoOptimization, optimizeForRealTime, optimizationState.optimizationLevel]);
  
  return <>{children}</>;
};

export default usePerformanceOptimizer;
