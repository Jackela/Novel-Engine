/**
 * Service Worker Registration for Mobile Optimization
 * ===================================================
 * 
 * Registers mobile-optimized service worker for better caching
 * and offline capabilities on mobile devices.
 */

// Check if service workers are supported
const isServiceWorkerSupported = 'serviceWorker' in navigator;

// Detect mobile devices
const isMobileDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
         window.innerWidth <= 768 ||
         'ontouchstart' in window ||
         navigator.maxTouchPoints > 0;
};

// Service worker registration configuration
interface SWConfig {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onOfflineReady?: () => void;
}

// Register service worker
export const registerServiceWorker = (config?: SWConfig): Promise<ServiceWorkerRegistration | null> => {
  // Only register on mobile devices in production
  if (!isServiceWorkerSupported || !isMobileDevice()) {
    console.log('Service Worker: Not registering (desktop or unsupported)');
    return Promise.resolve(null);
  }

  return navigator.serviceWorker
    .register('/sw-mobile.js', {
      scope: '/',
    })
    .then((registration) => {
      console.log('Service Worker: Registered successfully', registration.scope);

      // Check for updates
      registration.addEventListener('updatefound', () => {
        const installingWorker = registration.installing;
        
        if (installingWorker) {
          installingWorker.addEventListener('statechange', () => {
            if (installingWorker.state === 'installed') {
              if (navigator.serviceWorker.controller) {
                // New content available
                console.log('Service Worker: New content available');
                config?.onUpdate?.(registration);
              } else {
                // Content cached for offline use
                console.log('Service Worker: Content cached for offline use');
                config?.onSuccess?.(registration);
                config?.onOfflineReady?.();
              }
            }
          });
        }
      });

      return registration;
    })
    .catch((error) => {
      console.error('Service Worker: Registration failed', error);
      return null;
    });
};

// Unregister service worker
export const unregisterServiceWorker = (): Promise<boolean> => {
  if (!isServiceWorkerSupported) {
    return Promise.resolve(false);
  }

  return navigator.serviceWorker
    .getRegistrations()
    .then((registrations) => {
      return Promise.all(
        registrations.map((registration) => registration.unregister())
      );
    })
    .then((results) => {
      console.log('Service Worker: Unregistered');
      return results.every(Boolean);
    })
    .catch((error) => {
      console.error('Service Worker: Unregistration failed', error);
      return false;
    });
};

// Check if app is running standalone (installed as PWA)
export const isStandalone = (): boolean => {
  return window.matchMedia('(display-mode: standalone)').matches ||
         (window.navigator as unknown as { standalone?: boolean }).standalone === true;
};

// Get cache statistics
export const getCacheStats = (): Promise<Record<string, number>> => {
  if (!isServiceWorkerSupported || !navigator.serviceWorker.controller) {
    return Promise.resolve({});
  }

  return new Promise((resolve) => {
    const messageChannel = new MessageChannel();
    
    messageChannel.port1.onmessage = (event) => {
      resolve(event.data);
    };

    navigator.serviceWorker.controller.postMessage(
      { type: 'GET_CACHE_STATS' },
      [messageChannel.port2]
    );
  });
};

// Clear all caches
export const clearServiceWorkerCache = (): Promise<boolean> => {
  if (!isServiceWorkerSupported || !navigator.serviceWorker.controller) {
    return Promise.resolve(false);
  }

  return new Promise((resolve) => {
    const messageChannel = new MessageChannel();
    
    messageChannel.port1.onmessage = (event) => {
      resolve(event.data.success);
    };

    navigator.serviceWorker.controller.postMessage(
      { type: 'CLEAR_CACHE' },
      [messageChannel.port2]
    );
  });
};

// Mobile-specific optimizations
export const applyMobileOptimizations = (): void => {
  if (!isMobileDevice()) return;

  // Disable hover effects on mobile
  document.documentElement.classList.add('mobile-device');

  // Add mobile meta tags if not present
  if (!document.querySelector('meta[name="viewport"]')) {
    const viewport = document.createElement('meta');
    viewport.name = 'viewport';
    viewport.content = 'width=device-width, initial-scale=1, shrink-to-fit=no';
    document.head.appendChild(viewport);
  }

  // Add mobile web app meta tags
  const metaTags = [
    { name: 'mobile-web-app-capable', content: 'yes' },
    { name: 'apple-mobile-web-app-capable', content: 'yes' },
    { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
    { name: 'theme-color', content: '#667eea' },
  ];

  metaTags.forEach(({ name, content }) => {
    if (!document.querySelector(`meta[name="${name}"]`)) {
      const meta = document.createElement('meta');
      meta.name = name;
      meta.content = content;
      document.head.appendChild(meta);
    }
  });

  console.log('Mobile optimizations applied');
};

// Performance monitoring for mobile
export const monitorMobilePerformance = (): void => {
  if (!isMobileDevice()) return;

  // Monitor memory usage
    if ('memory' in performance) {
      const checkMemory = () => {
        const perf = performance as unknown as { memory?: { usedJSHeapSize: number } };
        const usedMB = (perf.memory?.usedJSHeapSize ?? 0) / (1024 * 1024);
      
      if (usedMB > 100) { // > 100MB
        console.warn('Mobile: High memory usage detected', `${usedMB.toFixed(2)}MB`);
        
        // Dispatch memory pressure event
        window.dispatchEvent(new CustomEvent('mobile-memory-pressure', {
          detail: { usage: usedMB }
        }));
      }
    };

    // Check memory every 30 seconds
    setInterval(checkMemory, 30000);
  }

  // Monitor network connection
  if ('connection' in navigator) {
    const connection = (navigator as unknown as { connection?: { effectiveType: string; downlink: number; saveData: boolean; addEventListener: (ev: string, cb: () => void) => void } }).connection;
    
    const logConnectionInfo = () => {
      console.log('Mobile: Network info', {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        saveData: connection.saveData
      });
      
      // Dispatch connection change event
      window.dispatchEvent(new CustomEvent('mobile-connection-change', {
        detail: {
          type: connection.effectiveType,
          downlink: connection.downlink,
          saveData: connection.saveData
        }
      }));
    };

    connection?.addEventListener('change', logConnectionInfo);
    if (connection) logConnectionInfo(); // Initial check
  }
};

// Initialize mobile optimizations
export const initializeMobileOptimizations = (config?: SWConfig): void => {
  if (!isMobileDevice()) return;

  console.log('Initializing mobile optimizations...');
  
  // Apply immediate optimizations
  applyMobileOptimizations();
  
  // Start performance monitoring
  monitorMobilePerformance();
  
  // Register service worker
  registerServiceWorker(config);
};

export default {
  registerServiceWorker,
  unregisterServiceWorker,
  getCacheStats,
  clearServiceWorkerCache,
  initializeMobileOptimizations,
  isMobileDevice
};
