import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import charactersSlice from './slices/charactersSlice';
import storiesSlice from './slices/storiesSlice';
import campaignsSlice from './slices/campaignsSlice';
import dashboardSlice from './slices/dashboardSlice';
import { mobileMemoryMiddleware } from './middleware/mobileMemoryMiddleware';
import { logger } from '../services/logging/LoggerFactory';

// Detect mobile device for memory optimizations
const isMobile = () => {
  if (typeof window === 'undefined') return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
         window.innerWidth <= 768;
};

export const store = configureStore({
  reducer: {
    auth: authSlice,
    characters: charactersSlice,
    stories: storiesSlice,
    campaigns: campaignsSlice,
    dashboard: dashboardSlice,
  },
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
    if (isMobile()) {
      middleware.concat(mobileMemoryMiddleware);
      logger.info('Mobile memory middleware enabled');
    }

    return middleware;
  },
  devTools: process.env.NODE_ENV !== 'production',
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;