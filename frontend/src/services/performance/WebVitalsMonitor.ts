/**
 * Web Vitals Monitoring Service
 * TDD: Service definition before tests (T018)
 * 
 * Constitution Alignment:
 * - Article II: Adapter (concrete implementation of IPerformanceMonitor)
 * - Article VII: Observability - Core Web Vitals tracking with structured logging
 */

import type { Metric } from 'web-vitals'
import type { IPerformanceMonitor, PerformanceMetric } from '@/types/accessibility'

export class WebVitalsMonitor implements IPerformanceMonitor {
  private metrics: Map<string, PerformanceMetric> = new Map()
  private reportToConsole: boolean
  private reportToAnalytics: boolean

  constructor(options: { reportToConsole?: boolean; reportToAnalytics?: boolean } = {}) {
    this.reportToConsole = options.reportToConsole ?? import.meta.env.DEV
    this.reportToAnalytics = options.reportToAnalytics ?? false
  }

  /**
   * Start tracking Core Web Vitals (LCP, FID, CLS, FCP, TTFB)
   * Uses dynamic import to avoid SSR issues
   */
  public trackWebVitals(): void {
    if (typeof window === 'undefined') return

    import('web-vitals').then(({ onCLS, onFID, onLCP, onFCP, onTTFB }) => {
      onCLS((metric) => this.handleMetric(metric))
      onFID((metric) => this.handleMetric(metric))
      onLCP((metric) => this.handleMetric(metric))
      onFCP((metric) => this.handleMetric(metric))
      onTTFB((metric) => this.handleMetric(metric))
    })
  }

  /**
   * Report custom performance metric
   */
  public reportMetric(metric: PerformanceMetric): void {
    this.metrics.set(metric.name, metric)

    if (this.reportToConsole) {
      this.logToConsole(metric)
    }

    if (this.reportToAnalytics) {
      this.sendToAnalytics(metric)
    }
  }

  /**
   * Get all tracked metrics
   */
  public getMetrics(): Map<string, PerformanceMetric> {
    return new Map(this.metrics)
  }

  /**
   * Get specific metric by name
   */
  public getMetric(name: string): PerformanceMetric | undefined {
    return this.metrics.get(name)
  }

  /**
   * Clear all tracked metrics
   */
  public clearMetrics(): void {
    this.metrics.clear()
  }

  /**
   * Handle Web Vitals metric callback
   */
  private handleMetric(metric: Metric): void {
    const performanceMetric = this.convertWebVitalsMetric(metric)
    this.reportMetric(performanceMetric)
  }

  /**
   * Convert Web Vitals metric to PerformanceMetric format
   */
  private convertWebVitalsMetric(metric: Metric): PerformanceMetric {
    let rating: 'good' | 'needs-improvement' | 'poor'

    // Rating thresholds based on Web Vitals recommendations
    // Source: https://web.dev/vitals/
    switch (metric.name) {
      case 'LCP': // Largest Contentful Paint
        rating = metric.value <= 2500 ? 'good' : metric.value <= 4000 ? 'needs-improvement' : 'poor'
        break
      case 'FID': // First Input Delay
        rating = metric.value <= 100 ? 'good' : metric.value <= 300 ? 'needs-improvement' : 'poor'
        break
      case 'CLS': // Cumulative Layout Shift
        rating = metric.value <= 0.1 ? 'good' : metric.value <= 0.25 ? 'needs-improvement' : 'poor'
        break
      case 'FCP': // First Contentful Paint
        rating = metric.value <= 1800 ? 'good' : metric.value <= 3000 ? 'needs-improvement' : 'poor'
        break
      case 'TTFB': // Time to First Byte
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

  /**
   * Log metric to console (development only)
   * Note: This console.log is intentional - it's gated by reportToConsole
   * which defaults to DEV mode only. Used for developer debugging of Web Vitals.
   */
  private logToConsole(metric: PerformanceMetric): void {
    const emoji = metric.rating === 'good' ? '✅' : metric.rating === 'needs-improvement' ? '⚠️' : '❌'

    // Development-only logging, controlled by reportToConsole flag
    console.log(
      `${emoji} [Web Vitals] ${metric.name}:`,
      {
        value: metric.name === 'CLS' ? metric.value.toFixed(3) : `${metric.value.toFixed(0)}ms`,
        rating: metric.rating,
        delta: metric.delta,
      }
    )
  }

  /**
   * Send metric to analytics service
   * Future: Integrate with LoggerFactory or analytics platform
   */
  private sendToAnalytics(metric: PerformanceMetric): void {
    if (!this.reportToAnalytics) {
      return
    }

    // TODO: Replace with proper analytics integration (e.g., LoggerFactory)
    // This debug logging is temporary until analytics service is integrated
    if (import.meta.env.DEV) {
      console.debug('[Web Vitals][analytics]', {
        metric: metric.name,
        value: metric.value,
        rating: metric.rating,
      })
    }
  }
}

/**
 * Singleton instance for application-wide use
 */
export const webVitalsMonitor = new WebVitalsMonitor({
  reportToConsole: import.meta.env.DEV,
  reportToAnalytics: import.meta.env.PROD,
})
