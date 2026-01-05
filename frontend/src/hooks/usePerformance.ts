/**
 * Performance Monitoring Hook
 * TDD: Hook definition before tests (T017)
 * Enhanced: T052 - Added re-render counting and interaction latency tracking
 * 
 * Constitution Alignment:
 * - Article II: Port interface (IPerformanceMonitor abstraction)
 * - Article VII: Observability - Core Web Vitals tracking
 */

import { useEffect, useRef } from 'react'
import type { Metric } from 'web-vitals'

export interface IPerformanceMonitor {
  trackWebVitals: () => void
  reportMetric: (metric: PerformanceMetric) => void
  getRenderCount: () => number
  measureInteraction: (name: string, callback: () => void) => void
}

export interface PerformanceMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  delta?: number
  id?: string
}

export interface WebVitalsMetrics {
  LCP?: number // Largest Contentful Paint (< 2.5s good)
  FID?: number // First Input Delay (< 100ms good)
  CLS?: number // Cumulative Layout Shift (< 0.1 good)
  FCP?: number // First Contentful Paint (< 1.8s good)
  TTFB?: number // Time to First Byte (< 600ms good)
}

export interface UsePerformanceOptions {
  onMetric?: (metric: PerformanceMetric) => void
  reportToAnalytics?: boolean
}

const METRIC_THRESHOLDS: Record<string, { good: number; ok: number }> = {
  LCP: { good: 2500, ok: 4000 },
  FID: { good: 100, ok: 300 },
  CLS: { good: 0.1, ok: 0.25 },
  FCP: { good: 1800, ok: 3000 },
  TTFB: { good: 600, ok: 1500 },
}

const getRatingForMetric = (name: string, value: number): PerformanceMetric['rating'] => {
  const thresholds = METRIC_THRESHOLDS[name]
  if (!thresholds) return 'needs-improvement'
  if (value <= thresholds.good) return 'good'
  if (value <= thresholds.ok) return 'needs-improvement'
  return 'poor'
}

const convertWebVitalsMetric = (metric: Metric): PerformanceMetric => ({
  name: metric.name,
  value: metric.value,
  rating: getRatingForMetric(metric.name, metric.value),
  delta: metric.delta,
  id: metric.id,
})

export function usePerformance(options: UsePerformanceOptions = {}): IPerformanceMonitor {
  const { onMetric, reportToAnalytics = false } = options
  const renderCount = useRef(0)
  const supportsWebVitals =
    typeof window !== 'undefined' &&
    typeof window.document !== 'undefined' &&
    typeof self !== 'undefined'
  const isTestEnv = import.meta.env.MODE === 'test'
  const shouldTrackWebVitals = supportsWebVitals && !isTestEnv

  // Track re-renders (T052)
  renderCount.current++

  const reportMetric = (metric: PerformanceMetric) => {
    // Report to callback
    onMetric?.(metric)

    // Development-only logging for performance debugging
    // This console.log is intentional and gated by DEV mode check
    if (import.meta.env.DEV) {
      console.log(`[Performance] ${metric.name}:`, {
        value: metric.value,
        rating: metric.rating,
        delta: metric.delta,
      })
    }

    // Report to analytics if enabled
    if (reportToAnalytics) {
      // Future: Send to LoggerFactory or analytics service
      // LoggerFactory.info('web_vitals', { metric })
    }
  }

  const trackWebVitals = () => {
    if (!shouldTrackWebVitals) return

    // Dynamic import to avoid bundling in SSR/test environments
    import('web-vitals')
      .then(({ onCLS, onFID, onLCP, onFCP, onTTFB }) => {
        onCLS((metric) => reportMetric(convertWebVitalsMetric(metric)))
        onFID((metric) => reportMetric(convertWebVitalsMetric(metric)))
        onLCP((metric) => reportMetric(convertWebVitalsMetric(metric)))
        onFCP((metric) => reportMetric(convertWebVitalsMetric(metric)))
        onTTFB((metric) => reportMetric(convertWebVitalsMetric(metric)))
      })
      .catch((error) => {
        if (import.meta.env.DEV) {
          console.warn('Web Vitals monitoring skipped:', error)
        }
      })
  }

  // Get render count (T052)
  const getRenderCount = () => renderCount.current

  // Measure interaction latency (T052)
  const measureInteraction = (name: string, callback: () => void) => {
    const startTime = performance.now()
    callback()
    const endTime = performance.now()
    const latency = endTime - startTime

    reportMetric({
      name: `interaction_${name}`,
      value: latency,
      rating: latency < 100 ? 'good' : latency < 300 ? 'needs-improvement' : 'poor',
    })
  }

  useEffect(() => {
    if (shouldTrackWebVitals) {
      trackWebVitals()
    }
    // Intentionally excluding trackWebVitals from deps:
    // - trackWebVitals is a stable function that only needs to run once on mount
    // - Including it would cause the web vitals listeners to be registered multiple times
    // - The function captures onMetric and reportToAnalytics via closure, which is correct
    //   since we want the initial configuration to persist
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldTrackWebVitals])

  return {
    trackWebVitals,
    reportMetric,
    getRenderCount,
    measureInteraction,
  }
}
