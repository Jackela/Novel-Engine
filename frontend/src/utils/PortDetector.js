/**
 * PortDetector.js - Automatic Port Detection and Configuration
 * 
 * Intelligently detects and configures the correct backend port
 * to prevent the critical port misconfiguration issue.
 * 
 * Features:
 * - Automatic port scanning and detection
 * - Environment-based configuration
 * - Fallback strategies for different setups
 */

import React from 'react';

/**
 * Additional features:
 * - Real-time health monitoring
 * - User-friendly error reporting
 */

import axios from 'axios';

// Common backend ports to check
const COMMON_BACKEND_PORTS = [8000, 8001, 3000, 5000, 8080, 8888];

// Default configurations for different environments
const ENV_CONFIGS = {
  development: {
    host: 'localhost',
    defaultPort: 8000,
    timeout: 3000
  },
  production: {
    host: window.location.hostname,
    defaultPort: 8000,
    timeout: 5000
  },
  docker: {
    host: 'backend',
    defaultPort: 8000,
    timeout: 5000
  }
};

/**
 * PortDetector Class
 * 
 * Handles automatic detection and configuration of backend ports
 */
export class PortDetector {
  constructor() {
    this.detectedConfig = null;
    this.lastHealthCheck = null;
    this.healthCheckInterval = null;
    this.listeners = new Set();
  }

  /**
   * Detect the correct backend configuration
   */
  async detectBackendConfig() {
    console.log('🔍 Starting backend port detection...');

    // Try environment variable first
    const envUrl = process.env.REACT_APP_API_URL;
    if (envUrl) {
      console.log(`📊 Checking environment URL: ${envUrl}`);
      const config = this.parseUrl(envUrl);
      if (await this.testConnection(config)) {
        this.detectedConfig = config;
        console.log(`✅ Environment configuration working: ${this.getBaseUrl(config)}`);
        return this.detectedConfig;
      }
    }

    // Determine environment
    const environment = this.detectEnvironment();
    const envConfig = ENV_CONFIGS[environment] || ENV_CONFIGS.development;
    
    console.log(`🌍 Detected environment: ${environment}`);

    // Try default configuration for environment
    console.log(`🎯 Testing default configuration for ${environment}...`);
    if (await this.testConnection(envConfig)) {
      this.detectedConfig = envConfig;
      console.log(`✅ Default configuration working: ${this.getBaseUrl(envConfig)}`);
      return this.detectedConfig;
    }

    // Scan common ports
    console.log('🔄 Scanning common backend ports...');
    for (const port of COMMON_BACKEND_PORTS) {
      const config = {
        host: envConfig.host,
        defaultPort: port,
        timeout: envConfig.timeout
      };

      console.log(`🔌 Testing port ${port}...`);
      if (await this.testConnection(config)) {
        this.detectedConfig = config;
        console.log(`✅ Found working backend on port ${port}: ${this.getBaseUrl(config)}`);
        return this.detectedConfig;
      }
    }

    // No working configuration found
    console.error('❌ No working backend configuration found');
    throw new Error('Unable to detect backend configuration');
  }

  /**
   * Test connection to a specific configuration
   */
  async testConnection(config) {
    try {
      const baseUrl = this.getBaseUrl(config);
      const healthEndpoint = `${baseUrl}/health`;
      
      const response = await axios.get(healthEndpoint, {
        timeout: config.timeout || 3000,
        headers: {
          'Accept': 'application/json'
        }
      });

      // Check if response indicates a healthy backend
      const isHealthy = response.status === 200 && 
                       (response.data?.status === 'healthy' || 
                        response.data?.message || 
                        response.status === 200);

      if (isHealthy) {
        console.log(`✅ Health check passed for ${baseUrl}:`, response.data);
        return true;
      }

      console.log(`⚠️ Health check failed for ${baseUrl}:`, response.data);
      return false;
    } catch (error) {
      // Log specific error types for debugging
      if (error.code === 'ECONNREFUSED') {
        console.log(`🚫 Connection refused on ${this.getBaseUrl(config)}`);
      } else if (error.code === 'ECONNABORTED') {
        console.log(`⏰ Timeout connecting to ${this.getBaseUrl(config)}`);
      } else {
        console.log(`❌ Error connecting to ${this.getBaseUrl(config)}:`, error.message);
      }
      return false;
    }
  }

  /**
   * Get the base URL for a configuration
   */
  getBaseUrl(config) {
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    return `${protocol}://${config.host}:${config.defaultPort}`;
  }

  /**
   * Parse URL string into configuration object
   */
  parseUrl(url) {
    try {
      const parsed = new URL(url);
      return {
        host: parsed.hostname,
        defaultPort: parseInt(parsed.port) || (parsed.protocol === 'https:' ? 443 : 80),
        timeout: 5000
      };
    } catch (error) {
      console.error('❌ Failed to parse URL:', url, error);
      return null;
    }
  }

  /**
   * Detect the current environment
   */
  detectEnvironment() {
    // Check for Docker environment
    if (window.location.hostname === 'localhost' && 
        process.env.NODE_ENV === 'development') {
      return 'development';
    }

    // Check for production environment
    if (process.env.NODE_ENV === 'production') {
      return 'production';
    }

    // Check for Docker container
    if (process.env.REACT_APP_DOCKER === 'true') {
      return 'docker';
    }

    return 'development';
  }

  /**
   * Get the current detected configuration
   */
  getConfig() {
    return this.detectedConfig;
  }

  /**
   * Get the API base URL
   */
  getApiBaseUrl() {
    if (!this.detectedConfig) {
      throw new Error('Backend configuration not detected. Call detectBackendConfig() first.');
    }
    return this.getBaseUrl(this.detectedConfig);
  }

  /**
   * Start health monitoring
   */
  startHealthMonitoring(interval = 30000) {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.healthCheckInterval = setInterval(async () => {
      try {
        await this.performHealthCheck();
      } catch (error) {
        console.warn('⚠️ Health check failed:', error.message);
        this.notifyListeners('health_check_failed', { error });
      }
    }, interval);

    console.log(`💓 Started health monitoring (${interval}ms interval)`);
  }

  /**
   * Stop health monitoring
   */
  stopHealthMonitoring() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
      console.log('🛑 Stopped health monitoring');
    }
  }

  /**
   * Perform a health check
   */
  async performHealthCheck() {
    if (!this.detectedConfig) {
      throw new Error('No configuration available for health check');
    }

    const isHealthy = await this.testConnection(this.detectedConfig);
    this.lastHealthCheck = {
      timestamp: new Date(),
      healthy: isHealthy,
      config: this.detectedConfig
    };

    this.notifyListeners('health_check_complete', this.lastHealthCheck);
    
    if (!isHealthy) {
      throw new Error('Backend health check failed');
    }

    return this.lastHealthCheck;
  }

  /**
   * Get the last health check result
   */
  getLastHealthCheck() {
    return this.lastHealthCheck;
  }

  /**
   * Add event listener
   */
  addEventListener(event, callback) {
    this.listeners.add({ event, callback });
  }

  /**
   * Remove event listener
   */
  removeEventListener(callback) {
    this.listeners.forEach(listener => {
      if (listener.callback === callback) {
        this.listeners.delete(listener);
      }
    });
  }

  /**
   * Notify all listeners of an event
   */
  notifyListeners(event, data) {
    this.listeners.forEach(listener => {
      if (listener.event === event) {
        try {
          listener.callback(data);
        } catch (error) {
          console.error('❌ Error in event listener:', error);
        }
      }
    });
  }

  /**
   * Reset detector state
   */
  reset() {
    this.stopHealthMonitoring();
    this.detectedConfig = null;
    this.lastHealthCheck = null;
    this.listeners.clear();
    console.log('🔄 PortDetector reset');
  }
}

/**
 * Global PortDetector instance
 */
export const globalPortDetector = new PortDetector();

/**
 * React hook for port detection
 */
export function usePortDetection() {
  const [config, setConfig] = React.useState(null);
  const [isDetecting, setIsDetecting] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [healthStatus, setHealthStatus] = React.useState(null);

  React.useEffect(() => {
    const handleHealthCheck = (result) => {
      setHealthStatus(result);
    };

    globalPortDetector.addEventListener('health_check_complete', handleHealthCheck);
    globalPortDetector.addEventListener('health_check_failed', (data) => {
      setHealthStatus({ healthy: false, error: data.error });
    });

    return () => {
      globalPortDetector.removeEventListener(handleHealthCheck);
    };
  }, []);

  const detectConfig = React.useCallback(async () => {
    setIsDetecting(true);
    setError(null);

    try {
      const detectedConfig = await globalPortDetector.detectBackendConfig();
      setConfig(detectedConfig);
      
      // Start health monitoring
      globalPortDetector.startHealthMonitoring();
      
      return detectedConfig;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsDetecting(false);
    }
  }, []);

  const getApiUrl = React.useCallback((path = '') => {
    if (!config) return null;
    const baseUrl = globalPortDetector.getBaseUrl(config);
    return `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  }, [config]);

  return {
    config,
    isDetecting,
    error,
    healthStatus,
    detectConfig,
    getApiUrl,
    detector: globalPortDetector
  };
}

export default PortDetector;