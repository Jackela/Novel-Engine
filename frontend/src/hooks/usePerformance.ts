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

export function usePerformance(options: UsePerformanceOptions = {}): IPerformanceMonitor {
  const { onMetric, reportToAnalytics = false } = options
  const renderCount = useRef(0)

  // Track re-renders (T052)
  renderCount.current++

  const reportMetric = (metric: PerformanceMetric) => {
    // Report to callback
    onMetric?.(metric)

    // Log to console in development
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

  const convertWebVitalsMetric = (metric: Metric): PerformanceMetric => {
    let rating: 'good' | 'needs-improvement' | 'poor'

    // Rating thresholds based on Web Vitals recommendations
    switch (metric.name) {
      case 'LCP':
        rating = metric.value <= 2500 ? 'good' : metric.value <= 4000 ? 'needs-improvement' : 'poor'
        break
      case 'FID':
        rating = metric.value <= 100 ? 'good' : metric.value <= 300 ? 'needs-improvement' : 'poor'
        break
      case 'CLS':
        rating = metric.value <= 0.1 ? 'good' : metric.value <= 0.25 ? 'needs-improvement' : 'poor'
        break
      case 'FCP':
        rating = metric.value <= 1800 ? 'good' : metric.value <= 3000 ? 'needs-improvement' : 'poor'
        break
      case 'TTFB':
        rating = metric.value <= 600 ? 'good' : metric.value <= 1500 ? 'needs-improvement' : 'poor'
        break
      default:
        rating = 'needs-improvement'
    }

    return {
      name: metric.name,
      value: metric.value,
      rating,
      delta: metric.delta,
      id: metric.id,
    }
  }

  const trackWebVitals = () => {
    if (typeof window === 'undefined') return

    // Dynamic import to avoid bundling in SSR
    import('web-vitals').then(({ onCLS, onFID, onLCP, onFCP, onTTFB }) => {
      onCLS((metric) => reportMetric(convertWebVitalsMetric(metric)))
      onFID((metric) => reportMetric(convertWebVitalsMetric(metric)))
      onLCP((metric) => reportMetric(convertWebVitalsMetric(metric)))
      onFCP((metric) => reportMetric(convertWebVitalsMetric(metric)))
      onTTFB((metric) => reportMetric(convertWebVitalsMetric(metric)))
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
    trackWebVitals()
  }, [])

  return {
    trackWebVitals,
    reportMetric,
    getRenderCount,
    measureInteraction,
  }
}
