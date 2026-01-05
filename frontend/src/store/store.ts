import { configureStore } from '@reduxjs/toolkit';
import { rootReducer } from './rootReducer';
import { mobileMemoryMiddleware } from './middleware/mobileMemoryMiddleware';
import { logger } from '@/services/logging/LoggerFactory';
import { isMobileDevice } from '@/utils/deviceDetection';

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) => {
    const middleware = getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'persist/PERSIST',
          'persist/REHYDRATE',
          '@@mobile-memory/CLEANUP',
          '@@mobile-memory/CHECK_PRESSURE',
          '@@mobile-memory/FORCE_CLEANUP'
        ],
      },
    });

    // Add mobile memory middleware on mobile devices
    if (isMobileDevice()) {
      logger.info('Mobile memory middleware enabled');
      return middleware.concat(mobileMemoryMiddleware);
    }

    return middleware;
  },
  devTools: process.env.NODE_ENV !== 'production',
});

// Expose store for E2E testing (development/test environments only)
if (typeof window !== 'undefined' && process.env.NODE_ENV !== 'production') {
  (window as Window & { __REDUX_STORE__?: typeof store }).__REDUX_STORE__ = store;
}

export type { RootState } from './rootReducer';
export type AppDispatch = typeof store.dispatch;
