/**
 * Mobile Memory Management Middleware for Redux
 * =============================================
 * 
 * Prevents excessive memory usage on mobile devices by:
 * - Limiting array sizes in state
 * - Cleaning up old data automatically
 * - Monitoring memory usage
 * - Implementing LRU cache behavior for large datasets
 */

import type { Middleware } from '@reduxjs/toolkit';
import type { RootState } from '@/store/store';
import { logger } from '@/services/logging/LoggerFactory';

// Mobile memory limits
const MOBILE_MEMORY_LIMITS = {
  MAX_HISTORY_ITEMS: 1000,
  MAX_CHARACTERS: 100,
  MAX_STORIES: 50,
  MAX_CAMPAIGNS: 20,
  MAX_DASHBOARD_EVENTS: 500,
  CLEANUP_THRESHOLD: 0.8, // Clean up when 80% full
};

// Track memory-sensitive slices
const MONITORED_SLICES = [
  'characters',
  'stories',
  'campaigns',
  'dashboard'
] as const;

// Memory monitoring utilities
class MobileMemoryManager {
  private lastCleanup = Date.now();
  private cleanupInterval = 5 * 60 * 1000; // 5 minutes

  shouldCleanup(): boolean {
    const now = Date.now();
    return (now - this.lastCleanup) > this.cleanupInterval;
  }

  getMemoryUsage(): number {
    const perf = performance as unknown as { memory?: { usedJSHeapSize: number } };
    const used = perf.memory?.usedJSHeapSize ?? 0;
    return used / (1024 * 1024); // MB
  }

  isMemoryPressure(): boolean {
    const usage = this.getMemoryUsage();
    return usage > 80; // > 80MB indicates memory pressure on mobile
  }

  markCleanup(): void {
    this.lastCleanup = Date.now();
  }

  // LRU cleanup for arrays
  cleanupArray<T extends { id?: string; timestamp?: number; createdAt?: string | Date }>(
    items: T[],
    maxSize: number
  ): T[] {
    if (items.length <= maxSize) return items;

    // Sort by timestamp (newest first)
    const sorted = [...items].sort((a, b) => {
      const aTime = a.timestamp || new Date(a.createdAt || 0).getTime();
      const bTime = b.timestamp || new Date(b.createdAt || 0).getTime();
      return bTime - aTime;
    });

    return sorted.slice(0, maxSize);
  }

  // Clean specific state slice
  cleanupSlice(state: unknown, sliceName: string): unknown {
    const s = state as Record<string, unknown>;
    switch (sliceName) {
      case 'characters':
        return {
          ...s,
          characters: this.cleanupArray(
            (s as Record<string, unknown>).characters as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            MOBILE_MEMORY_LIMITS.MAX_CHARACTERS
          ),
          recentActivity: this.cleanupArray(
            (s as Record<string, unknown>).recentActivity as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            100
          )
        };

      case 'stories':
        return {
          ...s,
          stories: this.cleanupArray(
            (s as Record<string, unknown>).stories as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            MOBILE_MEMORY_LIMITS.MAX_STORIES
          ),
          history: this.cleanupArray(
            (s as Record<string, unknown>).history as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            MOBILE_MEMORY_LIMITS.MAX_HISTORY_ITEMS
          )
        };

      case 'campaigns':
        return {
          ...s,
          campaigns: this.cleanupArray(
            (s as Record<string, unknown>).campaigns as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            MOBILE_MEMORY_LIMITS.MAX_CAMPAIGNS
          )
        };

      case 'dashboard':
        return {
          ...s,
          events: this.cleanupArray(
            (s as Record<string, unknown>).events as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            MOBILE_MEMORY_LIMITS.MAX_DASHBOARD_EVENTS
          ),
          notifications: this.cleanupArray(
            (s as Record<string, unknown>).notifications as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
            50
          ),
          metrics: {
            ...(s as Record<string, unknown>).metrics as Record<string, unknown>,
            history: this.cleanupArray(
              ((s as Record<string, unknown>).metrics as Record<string, unknown>)?.history as Array<{ id?: string; timestamp?: number; createdAt?: string | Date }> || [],
              200
            )
          }
        };

      default:
        return state;
    }
  }
}

const memoryManager = new MobileMemoryManager();

// Mobile memory middleware
export const mobileMemoryMiddleware: Middleware<{}, RootState> =
  (storeAPI) => (next) => (action) => {

    // Process the action first
    const result = next(action);

    // Check if cleanup is needed
    if (memoryManager.shouldCleanup() || memoryManager.isMemoryPressure()) {
      const state = storeAPI.getState();

      // Check if any slice needs cleanup
      let needsCleanup = false;
      const cleanedSlices: Partial<Record<(typeof MONITORED_SLICES)[number], unknown>> = {};

      MONITORED_SLICES.forEach(sliceName => {
        const sliceState = state[sliceName];
        if (sliceState) {
          const cleanedState = memoryManager.cleanupSlice(sliceState, sliceName);

          // Check if cleanup made changes
          const originalSize = JSON.stringify(sliceState).length;
          const cleanedSize = JSON.stringify(cleanedState).length;

          if (cleanedSize < originalSize) {
            cleanedSlices[sliceName] = cleanedState;
            needsCleanup = true;
          }
        }
      });

      // Dispatch cleanup action if needed
      if (needsCleanup) {
        logger.info('Mobile memory cleanup triggered:', {
          memoryUsage: memoryManager.getMemoryUsage(),
          cleanedSlices: Object.keys(cleanedSlices)
        });

        // Dispatch memory cleanup action
        storeAPI.dispatch({
          type: '@@mobile-memory/CLEANUP',
          payload: cleanedSlices
        });

        memoryManager.markCleanup();
      }
    }

    return result;
  };

// Memory pressure warning action
export const checkMemoryPressure = () => ({
  type: '@@mobile-memory/CHECK_PRESSURE',
  payload: {
    memoryUsage: memoryManager.getMemoryUsage(),
    isUnderPressure: memoryManager.isMemoryPressure()
  }
});

// Manual cleanup action
export const forceMemoryCleanup = () => ({
  type: '@@mobile-memory/FORCE_CLEANUP',
  payload: true
});

// Memory stats getter
export const getMemoryStats = () => ({
  usage: memoryManager.getMemoryUsage(),
  isUnderPressure: memoryManager.isMemoryPressure(),
  limits: MOBILE_MEMORY_LIMITS
});

export default mobileMemoryMiddleware;
