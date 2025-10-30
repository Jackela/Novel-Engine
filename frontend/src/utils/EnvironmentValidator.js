/**
 * EnvironmentValidator.js - Comprehensive Environment Validation
 * 
 * Validates system requirements and environment compatibility
 * for StoryForge AI optimal operation
 */

import React from 'react';

/**
 * Features:
 * - Browser compatibility checking
 * - System requirements validation
 * - Feature detection and polyfill suggestions
 * - Performance capability assessment
 * - Security requirements verification
 */

/**
 * Environment Requirements
 */
export const REQUIREMENTS = {
  browser: {
    chrome: { min: 90, recommended: 100 },
    firefox: { min: 88, recommended: 95 },
    safari: { min: 14, recommended: 15 },
    edge: { min: 90, recommended: 100 }
  },
  features: {
    required: [
      'fetch',
      'localStorage',
      'sessionStorage',
      'WebSocket',
      'Promise',
      'MutationObserver'
    ],
    recommended: [
      'IntersectionObserver',
      'ResizeObserver',
      'requestIdleCallback',
      'requestAnimationFrame'
    ]
  },
  performance: {
    minMemory: 2048, // MB
    recommendedMemory: 4096, // MB
    minCpuCores: 2,
    recommendedCpuCores: 4
  },
  security: {
    https: false, // Not required for localhost
    csp: false,   // Not strictly required
    cors: true    // Required for API calls
  }
};

/**
 * Validation Result Levels
 */
export const VALIDATION_LEVELS = {
  PASS: 'pass',
  WARNING: 'warning',
  FAIL: 'fail',
  UNKNOWN: 'unknown'
};

/**
 * EnvironmentValidator Class
 */
export class EnvironmentValidator {
  constructor() {
    this.validationResults = new Map();
    this.browserInfo = this.detectBrowser();
    this.systemInfo = this.detectSystem();
  }

  /**
   * Perform comprehensive environment validation
   */
  async validateEnvironment() {
    console.log('🔍 Starting environment validation...');

    const validationSuite = {
      browser: await this.validateBrowser(),
      features: await this.validateFeatures(),
      performance: await this.validatePerformance(),
      security: await this.validateSecurity(),
      network: await this.validateNetwork(),
      storage: await this.validateStorage()
    };

    const overallResult = this.calculateOverallValidation(validationSuite);

    const report = {
      timestamp: new Date().toISOString(),
      environment: {
        browser: this.browserInfo,
        system: this.systemInfo,
        userAgent: navigator.userAgent
      },
      validation: validationSuite,
      overall: overallResult,
      recommendations: this.generateRecommendations(validationSuite)
    };

    this.validationResults.set('latest', report);
    console.log('✅ Environment validation complete:', overallResult.level);

    return report;
  }

  /**
   * Validate browser compatibility
   */
  async validateBrowser() {
    const issues = [];
    const warnings = [];
    let level = VALIDATION_LEVELS.PASS;

    // Check browser type and version
    const browserCheck = this.checkBrowserVersion();
    if (browserCheck.level === VALIDATION_LEVELS.FAIL) {
      level = VALIDATION_LEVELS.FAIL;
      issues.push(browserCheck.message);
    } else if (browserCheck.level === VALIDATION_LEVELS.WARNING) {
      if (level === VALIDATION_LEVELS.PASS) level = VALIDATION_LEVELS.WARNING;
      warnings.push(browserCheck.message);
    }

    // Check for unsupported browsers
    const unsupportedBrowsers = ['Internet Explorer', 'Opera Mini'];
    if (unsupportedBrowsers.some(browser => navigator.userAgent.includes(browser))) {
      level = VALIDATION_LEVELS.FAIL;
      issues.push('Browser is not supported. Please use Chrome, Firefox, Safari, or Edge.');
    }

    // Check for mobile browsers with limitations
    if (this.systemInfo.isMobile && this.browserInfo.name === 'Safari' && this.browserInfo.version < 14) {
      level = VALIDATION_LEVELS.WARNING;
      warnings.push('Mobile Safari version may have limited functionality. Consider updating.');
    }

    return {
      level,
      score: this.calculateScore(level),
      issues,
      warnings,
      details: {
        browser: this.browserInfo,
        compatible: level !== VALIDATION_LEVELS.FAIL,
        recommended: level === VALIDATION_LEVELS.PASS && warnings.length === 0
      }
    };
  }

  /**
   * Validate required features
   */
  async validateFeatures() {
    const issues = [];
    const warnings = [];
    const missing = [];
    const available = [];

    // Check required features
    for (const feature of REQUIREMENTS.features.required) {
      const isAvailable = this.checkFeature(feature);
      if (isAvailable) {
        available.push(feature);
      } else {
        missing.push(feature);
        issues.push(`Required feature not available: ${feature}`);
      }
    }

    // Check recommended features
    const missingRecommended = [];
    for (const feature of REQUIREMENTS.features.recommended) {
      const isAvailable = this.checkFeature(feature);
      if (isAvailable) {
        available.push(feature);
      } else {
        missingRecommended.push(feature);
        warnings.push(`Recommended feature not available: ${feature}`);
      }
    }

    const level = missing.length > 0 ? VALIDATION_LEVELS.FAIL :
                 missingRecommended.length > 0 ? VALIDATION_LEVELS.WARNING :
                 VALIDATION_LEVELS.PASS;

    return {
      level,
      score: this.calculateScore(level),
      issues,
      warnings,
      details: {
        available,
        missing,
        missingRecommended,
        polyfillSuggestions: this.suggestPolyfills(missing.concat(missingRecommended))
      }
    };
  }

  /**
   * Validate performance capabilities
   */
  async validatePerformance() {
    const issues = [];
    const warnings = [];
    const metrics = {};

    // Memory check
    if (navigator.deviceMemory) {
      metrics.deviceMemory = navigator.deviceMemory * 1024; // Convert to MB
      if (metrics.deviceMemory < REQUIREMENTS.performance.minMemory) {
        issues.push(`Insufficient device memory: ${metrics.deviceMemory}MB (minimum: ${REQUIREMENTS.performance.minMemory}MB)`);
      } else if (metrics.deviceMemory < REQUIREMENTS.performance.recommendedMemory) {
        warnings.push(`Low device memory: ${metrics.deviceMemory}MB (recommended: ${REQUIREMENTS.performance.recommendedMemory}MB)`);
      }
    }

    // CPU check
    if (navigator.hardwareConcurrency) {
      metrics.cpuCores = navigator.hardwareConcurrency;
      if (metrics.cpuCores < REQUIREMENTS.performance.minCpuCores) {
        warnings.push(`Low CPU core count: ${metrics.cpuCores} (minimum: ${REQUIREMENTS.performance.minCpuCores})`);
      }
    }

    // Performance timing check
    const performanceCheck = await this.checkPerformanceCapability();
    metrics.performanceScore = performanceCheck.score;
    if (performanceCheck.score < 50) {
      issues.push('System performance may be insufficient for optimal experience');
    } else if (performanceCheck.score < 70) {
      warnings.push('System performance is below recommended levels');
    }

    // Connection check
    if (navigator.connection) {
      metrics.connection = {
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      };

      if (navigator.connection.effectiveType === 'slow-2g' || navigator.connection.effectiveType === '2g') {
        warnings.push('Slow network connection detected. Features may load slowly.');
      }
    }

    const level = issues.length > 0 ? VALIDATION_LEVELS.FAIL :
                 warnings.length > 0 ? VALIDATION_LEVELS.WARNING :
                 VALIDATION_LEVELS.PASS;

    return {
      level,
      score: this.calculateScore(level),
      issues,
      warnings,
      details: metrics
    };
  }

  /**
   * Validate security requirements
   */
  async validateSecurity() {
    const issues = [];
    const warnings = [];
    const securityFeatures = {};

    // HTTPS check (not required for localhost)
    const isHttps = window.location.protocol === 'https:';
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1';
    
    securityFeatures.https = isHttps;
    if (!isHttps && !isLocalhost) {
      warnings.push('HTTPS is recommended for production use');
    }

    // Content Security Policy check
    securityFeatures.csp = this.hasContentSecurityPolicy();
    
    // Secure context check
    securityFeatures.secureContext = window.isSecureContext;
    if (!window.isSecureContext && !isLocalhost) {
      warnings.push('Some features may be limited in non-secure contexts');
    }

    // Check for security-related features
    securityFeatures.features = {
      crypto: !!window.crypto && !!window.crypto.subtle,
      webAuthn: !!navigator.credentials,
      permissions: !!navigator.permissions
    };

    const level = issues.length > 0 ? VALIDATION_LEVELS.FAIL :
                 warnings.length > 0 ? VALIDATION_LEVELS.WARNING :
                 VALIDATION_LEVELS.PASS;

    return {
      level,
      score: this.calculateScore(level),
      issues,
      warnings,
      details: securityFeatures
    };
  }

  /**
   * Validate network capabilities
   */
  async validateNetwork() {
    const issues = [];
    const warnings = [];
    const networkInfo = {};

    try {
      // Network connection info
      if (navigator.connection) {
        networkInfo.connection = {
          type: navigator.connection.effectiveType,
          downlink: navigator.connection.downlink,
          rtt: navigator.connection.rtt,
          saveData: navigator.connection.saveData
        };
      }

      // Online status
      networkInfo.online = navigator.onLine;
      if (!navigator.onLine) {
        issues.push('No network connection detected');
      }

      // Test basic connectivity (if port detector is available)
      try {
        const testResponse = await fetch(window.location.origin, { 
          method: 'HEAD',
          cache: 'no-cache',
          timeout: 5000
        });
        networkInfo.reachable = testResponse.ok;
      } catch (error) {
        console.warn('Network connectivity test failed:', error);
        warnings.push('Network connectivity test failed');
        networkInfo.reachable = false;
      }

    } catch (error) {
      console.warn('Unable to perform network validation:', error);
      warnings.push('Unable to perform network validation');
    }

    const level = issues.length > 0 ? VALIDATION_LEVELS.FAIL :
                 warnings.length > 0 ? VALIDATION_LEVELS.WARNING :
                 VALIDATION_LEVELS.PASS;

    return {
      level,
      score: this.calculateScore(level),
      issues,
      warnings,
      details: networkInfo
    };
  }

  /**
   * Validate storage capabilities
   */
  async validateStorage() {
    const issues = [];
    const warnings = [];
    const storageInfo = {};

    // Local storage
    try {
      const testKey = 'storyforge_test';
      localStorage.setItem(testKey, 'test');
      localStorage.removeItem(testKey);
      storageInfo.localStorage = true;
    } catch (error) {
      console.warn('Local storage test failed:', error);
      storageInfo.localStorage = false;
      issues.push('Local storage is not available or restricted');
    }

    // Session storage
    try {
      const testKey = 'storyforge_test';
      sessionStorage.setItem(testKey, 'test');
      sessionStorage.removeItem(testKey);
      storageInfo.sessionStorage = true;
    } catch (error) {
      console.warn('Session storage test failed:', error);
      storageInfo.sessionStorage = false;
      warnings.push('Session storage is not available');
    }

    // IndexedDB
    storageInfo.indexedDB = !!window.indexedDB;
    if (!window.indexedDB) {
      warnings.push('IndexedDB not available - some features may be limited');
    }

    // Storage quota estimation
    if (navigator.storage && navigator.storage.estimate) {
      try {
        const estimate = await navigator.storage.estimate();
        storageInfo.quota = {
          usage: estimate.usage,
          quota: estimate.quota,
          available: estimate.quota - estimate.usage
        };

        if (estimate.quota < 50 * 1024 * 1024) { // 50MB
          warnings.push('Low storage quota may limit some features');
        }
      } catch (_error) {
        void _error;
        // Ignore quota estimation errors
      }
    }

    const level = issues.length > 0 ? VALIDATION_LEVELS.FAIL :
                 warnings.length > 0 ? VALIDATION_LEVELS.WARNING :
                 VALIDATION_LEVELS.PASS;

    return {
      level,
      score: this.calculateScore(level),
      issues,
      warnings,
      details: storageInfo
    };
  }

  /**
   * Browser detection utilities
   */
  detectBrowser() {
    const ua = navigator.userAgent;
    let browser = { name: 'Unknown', version: 0 };

    // Chrome
    const chromeMatch = ua.match(/Chrome\/(\d+)/);
    if (chromeMatch && !ua.includes('Edg')) {
      browser = { name: 'Chrome', version: parseInt(chromeMatch[1]) };
    }
    
    // Firefox
    const firefoxMatch = ua.match(/Firefox\/(\d+)/);
    if (firefoxMatch) {
      browser = { name: 'Firefox', version: parseInt(firefoxMatch[1]) };
    }
    
    // Safari
    const safariMatch = ua.match(/Version\/(\d+).*Safari/);
    if (safariMatch && !ua.includes('Chrome')) {
      browser = { name: 'Safari', version: parseInt(safariMatch[1]) };
    }
    
    // Edge
    const edgeMatch = ua.match(/Edg\/(\d+)/);
    if (edgeMatch) {
      browser = { name: 'Edge', version: parseInt(edgeMatch[1]) };
    }

    return browser;
  }

  detectSystem() {
    const ua = navigator.userAgent;
    return {
      platform: navigator.platform,
      isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua),
      isTablet: /iPad|Android.*(?!.*Mobile)/i.test(ua),
      isDesktop: !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua),
      os: this.detectOS(ua),
      touchSupport: 'ontouchstart' in window,
      deviceMemory: navigator.deviceMemory,
      hardwareConcurrency: navigator.hardwareConcurrency
    };
  }

  detectOS(ua) {
    if (ua.includes('Windows')) return 'Windows';
    if (ua.includes('Mac OS')) return 'macOS';
    if (ua.includes('Linux')) return 'Linux';
    if (ua.includes('Android')) return 'Android';
    if (ua.includes('iOS')) return 'iOS';
    return 'Unknown';
  }

  /**
   * Feature checking utilities
   */
  checkFeature(feature) {
    switch (feature) {
      case 'fetch': return !!window.fetch;
      case 'localStorage': return !!window.localStorage;
      case 'sessionStorage': return !!window.sessionStorage;
      case 'WebSocket': return !!window.WebSocket;
      case 'Promise': return !!window.Promise;
      case 'MutationObserver': return !!window.MutationObserver;
      case 'IntersectionObserver': return !!window.IntersectionObserver;
      case 'ResizeObserver': return !!window.ResizeObserver;
      case 'requestIdleCallback': return !!window.requestIdleCallback;
      case 'requestAnimationFrame': return !!window.requestAnimationFrame;
      default: return false;
    }
  }

  checkBrowserVersion() {
    const browser = this.browserInfo;
    const requirements = REQUIREMENTS.browser[browser.name.toLowerCase()];

    if (!requirements) {
      return {
        level: VALIDATION_LEVELS.WARNING,
        message: `Browser ${browser.name} compatibility unknown`
      };
    }

    if (browser.version < requirements.min) {
      return {
        level: VALIDATION_LEVELS.FAIL,
        message: `Browser version ${browser.version} is below minimum requirement (${requirements.min})`
      };
    }

    if (browser.version < requirements.recommended) {
      return {
        level: VALIDATION_LEVELS.WARNING,
        message: `Browser version ${browser.version} is below recommended (${requirements.recommended})`
      };
    }

    return {
      level: VALIDATION_LEVELS.PASS,
      message: `Browser ${browser.name} ${browser.version} is fully supported`
    };
  }

  async checkPerformanceCapability() {
    return new Promise((resolve) => {
      const startTime = performance.now();
      let score = 100;

      // Simple performance test
      setTimeout(() => {
        const endTime = performance.now();
        const delay = endTime - startTime;

        // Adjust score based on timer accuracy
        if (delay > 20) score -= 20;
        if (delay > 50) score -= 30;

        // Check memory performance
        if (performance.memory) {
          const memoryRatio = performance.memory.usedJSHeapSize / performance.memory.totalJSHeapSize;
          if (memoryRatio > 0.8) score -= 20;
        }

        resolve({ score: Math.max(0, score) });
      }, 10);
    });
  }

  hasContentSecurityPolicy() {
    // Check for CSP meta tag or header
    const cspMeta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
    return !!cspMeta;
  }

  /**
   * Utility methods
   */
  suggestPolyfills(missingFeatures) {
    const polyfills = {
      'fetch': 'whatwg-fetch',
      'Promise': 'es6-promise',
      'IntersectionObserver': 'intersection-observer',
      'ResizeObserver': 'resize-observer-polyfill',
      'requestIdleCallback': 'requestidlecallback'
    };

    return missingFeatures.map(feature => polyfills[feature]).filter(Boolean);
  }

  calculateScore(level) {
    switch (level) {
      case VALIDATION_LEVELS.PASS: return 100;
      case VALIDATION_LEVELS.WARNING: return 75;
      case VALIDATION_LEVELS.FAIL: return 25;
      default: return 50;
    }
  }

  calculateOverallValidation(validationSuite) {
    const weights = {
      browser: 0.25,
      features: 0.25,
      performance: 0.2,
      security: 0.1,
      network: 0.1,
      storage: 0.1
    };

    let totalScore = 0;
    let failCount = 0;
    let warningCount = 0;

    for (const [category, result] of Object.entries(validationSuite)) {
      const weight = weights[category] || 0;
      totalScore += result.score * weight;

      if (result.level === VALIDATION_LEVELS.FAIL) failCount++;
      else if (result.level === VALIDATION_LEVELS.WARNING) warningCount++;
    }

    let level;
    if (failCount > 0) {
      level = VALIDATION_LEVELS.FAIL;
    } else if (warningCount > 0) {
      level = VALIDATION_LEVELS.WARNING;
    } else {
      level = VALIDATION_LEVELS.PASS;
    }

    return {
      level,
      score: Math.round(totalScore),
      summary: this.generateValidationSummary(level, totalScore, failCount, warningCount)
    };
  }

  generateValidationSummary(level, score, failCount, warningCount) {
    switch (level) {
      case VALIDATION_LEVELS.PASS:
        return `Environment is fully compatible (${score}% score)`;
      case VALIDATION_LEVELS.WARNING:
        return `Environment is compatible with ${warningCount} warning${warningCount > 1 ? 's' : ''} (${score}% score)`;
      case VALIDATION_LEVELS.FAIL:
        return `Environment has ${failCount} critical issue${failCount > 1 ? 's' : ''} (${score}% score)`;
      default:
        return `Environment validation status unknown`;
    }
  }

  generateRecommendations(validationSuite) {
    const recommendations = [];

    for (const [category, result] of Object.entries(validationSuite)) {
      if (result.level === VALIDATION_LEVELS.FAIL) {
        switch (category) {
          case 'browser':
            recommendations.push('Update your browser to the latest version for optimal compatibility');
            break;
          case 'features':
            recommendations.push('Your browser is missing required features. Consider updating or switching browsers');
            break;
          case 'performance':
            recommendations.push('System performance may be insufficient. Close other applications or upgrade hardware');
            break;
          case 'storage':
            recommendations.push('Enable local storage in your browser settings');
            break;
          case 'network':
            recommendations.push('Check your network connection and try again');
            break;
        }
      } else if (result.level === VALIDATION_LEVELS.WARNING) {
        switch (category) {
          case 'browser':
            recommendations.push('Consider updating your browser for the best experience');
            break;
          case 'features':
            recommendations.push('Some advanced features may not be available in your browser');
            break;
          case 'performance':
            recommendations.push('Consider closing other applications for better performance');
            break;
          case 'security':
            recommendations.push('Use HTTPS for enhanced security when possible');
            break;
        }
      }
    }

    if (recommendations.length === 0) {
      recommendations.push('Your environment is fully optimized for StoryForge AI!');
    }

    return recommendations;
  }

  /**
   * Get validation results
   */
  getLatestValidation() {
    return this.validationResults.get('latest');
  }

  /**
   * Reset validator
   */
  reset() {
    this.validationResults.clear();
    console.log('🔄 Environment validator reset');
  }
}

/**
 * Global environment validator instance
 */
export const globalEnvironmentValidator = new EnvironmentValidator();

/**
 * React hook for environment validation
 */
export function useEnvironmentValidator() {
  const [validationData, setValidationData] = React.useState(null);
  const [isValidating, setIsValidating] = React.useState(false);

  const validateEnvironment = React.useCallback(async () => {
    setIsValidating(true);
    try {
      const result = await globalEnvironmentValidator.validateEnvironment();
      setValidationData(result);
      return result;
    } finally {
      setIsValidating(false);
    }
  }, []);

  return {
    validationData,
    isValidating,
    validateEnvironment,
    validator: globalEnvironmentValidator
  };
}

export default EnvironmentValidator;
