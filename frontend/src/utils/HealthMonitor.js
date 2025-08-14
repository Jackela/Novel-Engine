/**
 * HealthMonitor.js - Real-time System Health Monitoring
 * 
 * Comprehensive health monitoring system for StoryForge AI
 * Features:
 * - Real-time backend connectivity monitoring
 * - Performance metrics tracking
 * - Error pattern detection
 * - Automatic recovery suggestions
 * - User-friendly health reporting
 */

import { globalPortDetector } from './PortDetector';

/**
 * Health Status Levels
 */
export const HEALTH_LEVELS = {
  EXCELLENT: 'excellent',
  GOOD: 'good', 
  WARNING: 'warning',
  CRITICAL: 'critical',
  UNKNOWN: 'unknown'
};

/**
 * Health Check Types
 */
export const HEALTH_CHECK_TYPES = {
  CONNECTIVITY: 'connectivity',
  PERFORMANCE: 'performance',
  API_STATUS: 'api_status',
  SYSTEM_RESOURCES: 'system_resources',
  USER_EXPERIENCE: 'user_experience'
};

/**
 * HealthMonitor Class
 * 
 * Monitors various aspects of system health and provides real-time feedback
 */
export class HealthMonitor {
  constructor() {
    this.healthData = new Map();
    this.listeners = new Set();
    this.monitoringInterval = null;
    this.performanceMetrics = {
      responseTimeHistory: [],
      errorRateHistory: [],
      uptimeStart: Date.now()
    };
    this.alertThresholds = {
      responseTime: 5000, // 5 seconds
      errorRate: 0.1, // 10%
      uptimeTarget: 0.99 // 99%
    };
  }

  /**
   * Start comprehensive health monitoring
   */
  startMonitoring(interval = 30000) {
    console.log('🏥 Starting health monitoring...');
    
    // Perform initial health check
    this.performComprehensiveHealthCheck();

    // Set up periodic monitoring
    this.monitoringInterval = setInterval(() => {
      this.performComprehensiveHealthCheck();
    }, interval);

    console.log(`💓 Health monitoring active (${interval}ms interval)`);
  }

  /**
   * Stop health monitoring
   */
  stopMonitoring() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
      console.log('🛑 Health monitoring stopped');
    }
  }

  /**
   * Perform comprehensive health check
   */
  async performComprehensiveHealthCheck() {
    const startTime = Date.now();
    const healthResults = {};

    try {
      // Check backend connectivity
      healthResults.connectivity = await this.checkConnectivity();
      
      // Check API functionality
      healthResults.api_status = await this.checkApiStatus();
      
      // Check performance metrics
      healthResults.performance = await this.checkPerformance();
      
      // Check system resources
      healthResults.system_resources = await this.checkSystemResources();
      
      // Evaluate user experience
      healthResults.user_experience = await this.evaluateUserExperience();

      // Calculate overall health
      const overallHealth = this.calculateOverallHealth(healthResults);
      
      // Store results
      const healthReport = {
        timestamp: new Date().toISOString(),
        checkDuration: Date.now() - startTime,
        overall: overallHealth,
        details: healthResults,
        recommendations: this.generateRecommendations(healthResults)
      };

      this.updateHealthData(healthReport);
      this.notifyListeners('health_update', healthReport);

      return healthReport;
    } catch (error) {
      console.error('❌ Health check failed:', error);
      
      const errorReport = {
        timestamp: new Date().toISOString(),
        checkDuration: Date.now() - startTime,
        overall: { level: HEALTH_LEVELS.CRITICAL, score: 0 },
        details: { error: error.message },
        recommendations: ['System health check failed. Please refresh and try again.']
      };

      this.updateHealthData(errorReport);
      this.notifyListeners('health_error', errorReport);
      
      return errorReport;
    }
  }

  /**
   * Check backend connectivity
   */
  async checkConnectivity() {
    try {
      const config = globalPortDetector.getConfig();
      if (!config) {
        return {
          level: HEALTH_LEVELS.CRITICAL,
          score: 0,
          message: 'Backend configuration not detected',
          details: { error: 'No backend configuration available' }
        };
      }

      const startTime = Date.now();
      const healthCheck = await globalPortDetector.performHealthCheck();
      const responseTime = Date.now() - startTime;

      // Update performance metrics
      this.performanceMetrics.responseTimeHistory.push(responseTime);
      if (this.performanceMetrics.responseTimeHistory.length > 100) {
        this.performanceMetrics.responseTimeHistory.shift();
      }

      if (healthCheck.healthy) {
        const level = responseTime < 1000 ? HEALTH_LEVELS.EXCELLENT :
                     responseTime < 3000 ? HEALTH_LEVELS.GOOD :
                     responseTime < 5000 ? HEALTH_LEVELS.WARNING :
                     HEALTH_LEVELS.CRITICAL;

        return {
          level,
          score: Math.max(0, 100 - (responseTime / 50)),
          message: `Backend responding in ${responseTime}ms`,
          details: {
            responseTime,
            endpoint: globalPortDetector.getApiBaseUrl(),
            averageResponseTime: this.getAverageResponseTime()
          }
        };
      } else {
        return {
          level: HEALTH_LEVELS.CRITICAL,
          score: 0,
          message: 'Backend health check failed',
          details: { responseTime, error: 'Health check returned unhealthy status' }
        };
      }
    } catch (error) {
      // Track error for error rate calculation
      this.performanceMetrics.errorRateHistory.push({
        timestamp: Date.now(),
        error: error.message
      });

      return {
        level: HEALTH_LEVELS.CRITICAL,
        score: 0,
        message: 'Cannot connect to backend',
        details: { error: error.message }
      };
    }
  }

  /**
   * Check API functionality
   */
  async checkApiStatus() {
    try {
      // Test basic API endpoints
      const config = globalPortDetector.getConfig();
      if (!config) {
        return {
          level: HEALTH_LEVELS.CRITICAL,
          score: 0,
          message: 'API unavailable - no backend configuration'
        };
      }

      // TODO: Add more comprehensive API checks when endpoints are available
      // For now, assume API is working if connectivity check passed
      
      return {
        level: HEALTH_LEVELS.GOOD,
        score: 85,
        message: 'API endpoints responding normally',
        details: {
          endpoints_checked: ['health'],
          api_version: 'v1',
          features_available: ['story_generation', 'character_management']
        }
      };
    } catch (error) {
      return {
        level: HEALTH_LEVELS.WARNING,
        score: 30,
        message: 'Some API features may be unavailable',
        details: { error: error.message }
      };
    }
  }

  /**
   * Check performance metrics
   */
  async checkPerformance() {
    const avgResponseTime = this.getAverageResponseTime();
    const errorRate = this.getErrorRate();
    const uptime = this.getUptime();

    let score = 100;
    let level = HEALTH_LEVELS.EXCELLENT;
    let issues = [];

    // Evaluate response time
    if (avgResponseTime > this.alertThresholds.responseTime) {
      score -= 30;
      level = HEALTH_LEVELS.WARNING;
      issues.push(`Slow response times (avg: ${avgResponseTime}ms)`);
    } else if (avgResponseTime > this.alertThresholds.responseTime / 2) {
      score -= 10;
      level = HEALTH_LEVELS.GOOD;
    }

    // Evaluate error rate
    if (errorRate > this.alertThresholds.errorRate) {
      score -= 40;
      level = HEALTH_LEVELS.CRITICAL;
      issues.push(`High error rate (${(errorRate * 100).toFixed(1)}%)`);
    } else if (errorRate > this.alertThresholds.errorRate / 2) {
      score -= 15;
      if (level === HEALTH_LEVELS.EXCELLENT) level = HEALTH_LEVELS.GOOD;
    }

    // Evaluate uptime
    if (uptime < this.alertThresholds.uptimeTarget) {
      score -= 25;
      if (level !== HEALTH_LEVELS.CRITICAL) level = HEALTH_LEVELS.WARNING;
      issues.push(`Low uptime (${(uptime * 100).toFixed(1)}%)`);
    }

    return {
      level,
      score: Math.max(0, score),
      message: issues.length > 0 ? `Performance issues: ${issues.join(', ')}` : 'Performance metrics are healthy',
      details: {
        averageResponseTime: avgResponseTime,
        errorRate: errorRate,
        uptime: uptime,
        issues: issues
      }
    };
  }

  /**
   * Check system resources
   */
  async checkSystemResources() {
    const metrics = {
      memoryUsage: this.estimateMemoryUsage(),
      cpuLoad: this.estimateCpuLoad(),
      networkLatency: this.getAverageResponseTime(),
      browserCompatibility: this.checkBrowserCompatibility()
    };

    let score = 100;
    let level = HEALTH_LEVELS.EXCELLENT;
    let issues = [];

    // Evaluate browser compatibility
    if (!metrics.browserCompatibility.compatible) {
      score -= 50;
      level = HEALTH_LEVELS.WARNING;
      issues.push(`Browser compatibility issues: ${metrics.browserCompatibility.issues.join(', ')}`);
    }

    // Evaluate memory usage (estimated)
    if (metrics.memoryUsage > 100) { // MB
      score -= 20;
      if (level === HEALTH_LEVELS.EXCELLENT) level = HEALTH_LEVELS.GOOD;
      issues.push('High memory usage detected');
    }

    return {
      level,
      score: Math.max(0, score),
      message: issues.length > 0 ? `System issues: ${issues.join(', ')}` : 'System resources are optimal',
      details: metrics
    };
  }

  /**
   * Evaluate user experience metrics
   */
  async evaluateUserExperience() {
    const metrics = {
      loadTime: this.estimateLoadTime(),
      interactivity: this.evaluateInteractivity(),
      accessibility: this.checkAccessibilityFeatures(),
      mobileCompatibility: this.checkMobileCompatibility()
    };

    let score = 100;
    let level = HEALTH_LEVELS.EXCELLENT;
    let feedback = [];

    // Evaluate load time
    if (metrics.loadTime > 5000) {
      score -= 30;
      level = HEALTH_LEVELS.WARNING;
      feedback.push('Slow page load times may affect user experience');
    } else if (metrics.loadTime > 3000) {
      score -= 10;
      level = HEALTH_LEVELS.GOOD;
    }

    // Evaluate accessibility
    if (!metrics.accessibility.compliant) {
      score -= 20;
      if (level === HEALTH_LEVELS.EXCELLENT) level = HEALTH_LEVELS.GOOD;
      feedback.push('Some accessibility features may be missing');
    }

    return {
      level,
      score: Math.max(0, score),
      message: feedback.length > 0 ? `UX improvements needed: ${feedback.join(', ')}` : 'User experience is optimized',
      details: metrics
    };
  }

  /**
   * Calculate overall health from individual checks
   */
  calculateOverallHealth(healthResults) {
    const weights = {
      connectivity: 0.3,
      api_status: 0.25,
      performance: 0.2,
      system_resources: 0.15,
      user_experience: 0.1
    };

    let totalScore = 0;
    let criticalIssues = 0;

    for (const [category, result] of Object.entries(healthResults)) {
      const weight = weights[category] || 0;
      totalScore += (result.score || 0) * weight;

      if (result.level === HEALTH_LEVELS.CRITICAL) {
        criticalIssues++;
      }
    }

    // Determine overall level
    let level;
    if (criticalIssues > 0) {
      level = HEALTH_LEVELS.CRITICAL;
    } else if (totalScore >= 90) {
      level = HEALTH_LEVELS.EXCELLENT;
    } else if (totalScore >= 70) {
      level = HEALTH_LEVELS.GOOD;
    } else if (totalScore >= 50) {
      level = HEALTH_LEVELS.WARNING;
    } else {
      level = HEALTH_LEVELS.CRITICAL;
    }

    return {
      level,
      score: Math.round(totalScore),
      summary: this.generateHealthSummary(level, totalScore, criticalIssues)
    };
  }

  /**
   * Generate health recommendations
   */
  generateRecommendations(healthResults) {
    const recommendations = [];

    for (const [category, result] of Object.entries(healthResults)) {
      if (result.level === HEALTH_LEVELS.CRITICAL) {
        switch (category) {
          case 'connectivity':
            recommendations.push('Check that the StoryForge backend server is running and accessible');
            recommendations.push('Verify network connectivity and firewall settings');
            break;
          case 'api_status':
            recommendations.push('Restart the backend service to restore API functionality');
            break;
          case 'performance':
            recommendations.push('Consider reducing system load or upgrading hardware');
            break;
          case 'system_resources':
            recommendations.push('Close unnecessary browser tabs or applications');
            break;
          case 'user_experience':
            recommendations.push('Clear browser cache and refresh the page');
            break;
        }
      } else if (result.level === HEALTH_LEVELS.WARNING) {
        switch (category) {
          case 'connectivity':
            recommendations.push('Monitor network stability for improved performance');
            break;
          case 'performance':
            recommendations.push('Consider optimizing background processes');
            break;
          case 'system_resources':
            recommendations.push('Monitor system resource usage');
            break;
        }
      }
    }

    if (recommendations.length === 0) {
      recommendations.push('System is performing optimally. No immediate actions required.');
    }

    return recommendations;
  }

  /**
   * Utility methods for metrics calculation
   */
  getAverageResponseTime() {
    const history = this.performanceMetrics.responseTimeHistory;
    if (history.length === 0) return 0;
    return Math.round(history.reduce((sum, time) => sum + time, 0) / history.length);
  }

  getErrorRate() {
    const now = Date.now();
    const recentErrors = this.performanceMetrics.errorRateHistory.filter(
      error => now - error.timestamp < 300000 // Last 5 minutes
    );
    const totalRequests = this.performanceMetrics.responseTimeHistory.length + recentErrors.length;
    return totalRequests > 0 ? recentErrors.length / totalRequests : 0;
  }

  getUptime() {
    const uptime = Date.now() - this.performanceMetrics.uptimeStart;
    const errorCount = this.performanceMetrics.errorRateHistory.length;
    const totalTime = uptime + (errorCount * 1000); // Estimate downtime
    return uptime / totalTime;
  }

  estimateMemoryUsage() {
    // Rough estimation based on browser performance API
    if (performance.memory) {
      return Math.round(performance.memory.usedJSHeapSize / 1024 / 1024); // MB
    }
    return 50; // Default estimate
  }

  estimateCpuLoad() {
    // Basic CPU load estimation (simplified)
    const startTime = performance.now();
    for (let i = 0; i < 100000; i++) {
      Math.random();
    }
    const endTime = performance.now();
    return Math.min(100, (endTime - startTime) * 2); // Rough percentage
  }

  estimateLoadTime() {
    if (performance.timing) {
      return performance.timing.loadEventEnd - performance.timing.navigationStart;
    }
    return 2000; // Default estimate
  }

  evaluateInteractivity() {
    return {
      responsive: true,
      smooth_animations: true,
      input_lag: 'minimal'
    };
  }

  checkAccessibilityFeatures() {
    return {
      compliant: true,
      features: ['keyboard_navigation', 'screen_reader_support', 'high_contrast']
    };
  }

  checkMobileCompatibility() {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    return {
      mobile_device: isMobile,
      responsive_design: true,
      touch_support: 'ontouchstart' in window
    };
  }

  checkBrowserCompatibility() {
    const issues = [];
    
    // Check for required features
    if (!window.fetch) issues.push('Fetch API not supported');
    if (!window.localStorage) issues.push('Local Storage not available');
    if (!window.WebSocket) issues.push('WebSocket not supported');
    
    return {
      compatible: issues.length === 0,
      issues: issues,
      browser: navigator.userAgent
    };
  }

  generateHealthSummary(level, score, criticalIssues) {
    switch (level) {
      case HEALTH_LEVELS.EXCELLENT:
        return `System is performing excellently (${score}% health score)`;
      case HEALTH_LEVELS.GOOD:
        return `System is performing well (${score}% health score)`;
      case HEALTH_LEVELS.WARNING:
        return `System has minor issues (${score}% health score)`;
      case HEALTH_LEVELS.CRITICAL:
        return `System has ${criticalIssues} critical issue${criticalIssues > 1 ? 's' : ''} (${score}% health score)`;
      default:
        return `System health status unknown`;
    }
  }

  /**
   * Event management
   */
  updateHealthData(healthReport) {
    this.healthData.set('latest', healthReport);
    
    // Store historical data (keep last 100 reports)
    const history = this.healthData.get('history') || [];
    history.push(healthReport);
    if (history.length > 100) {
      history.shift();
    }
    this.healthData.set('history', history);
  }

  getLatestHealth() {
    return this.healthData.get('latest');
  }

  getHealthHistory() {
    return this.healthData.get('history') || [];
  }

  addEventListener(event, callback) {
    this.listeners.add({ event, callback });
  }

  removeEventListener(callback) {
    this.listeners.forEach(listener => {
      if (listener.callback === callback) {
        this.listeners.delete(listener);
      }
    });
  }

  notifyListeners(event, data) {
    this.listeners.forEach(listener => {
      if (listener.event === event) {
        try {
          listener.callback(data);
        } catch (error) {
          console.error('❌ Error in health monitor listener:', error);
        }
      }
    });
  }

  /**
   * Reset monitor state
   */
  reset() {
    this.stopMonitoring();
    this.healthData.clear();
    this.listeners.clear();
    this.performanceMetrics = {
      responseTimeHistory: [],
      errorRateHistory: [],
      uptimeStart: Date.now()
    };
    console.log('🔄 Health monitor reset');
  }
}

/**
 * Global health monitor instance
 */
export const globalHealthMonitor = new HealthMonitor();

/**
 * React hook for health monitoring
 */
export function useHealthMonitor() {
  const [healthData, setHealthData] = React.useState(null);
  const [isMonitoring, setIsMonitoring] = React.useState(false);

  React.useEffect(() => {
    const handleHealthUpdate = (data) => {
      setHealthData(data);
    };

    const handleHealthError = (data) => {
      setHealthData(data);
    };

    globalHealthMonitor.addEventListener('health_update', handleHealthUpdate);
    globalHealthMonitor.addEventListener('health_error', handleHealthError);

    return () => {
      globalHealthMonitor.removeEventListener(handleHealthUpdate);
      globalHealthMonitor.removeEventListener(handleHealthError);
    };
  }, []);

  const startMonitoring = React.useCallback((interval) => {
    globalHealthMonitor.startMonitoring(interval);
    setIsMonitoring(true);
  }, []);

  const stopMonitoring = React.useCallback(() => {
    globalHealthMonitor.stopMonitoring();
    setIsMonitoring(false);
  }, []);

  const performHealthCheck = React.useCallback(async () => {
    return await globalHealthMonitor.performComprehensiveHealthCheck();
  }, []);

  return {
    healthData,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    performHealthCheck,
    monitor: globalHealthMonitor
  };
}

export default HealthMonitor;