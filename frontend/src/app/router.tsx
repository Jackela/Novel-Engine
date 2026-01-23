/**
 * TanStack Router Configuration
 * Type-safe routing with code splitting
 */
import {
  createRouter,
  createRoute,
  createRootRoute,
  redirect,
  lazyRouteComponent,
} from '@tanstack/react-router';
import { RootLayout } from './layout';
import { ProtectedLayout } from './ProtectedLayout';
import { useAuthStore } from '@/features/auth';

type AuthStoreWithPersist = typeof useAuthStore & {
  persist?: {
    hasHydrated: () => boolean;
    rehydrate: () => Promise<void>;
  };
};

// Auth check function using Zustand store
const isAuthenticated = () => {
  const state = useAuthStore.getState();
  return state.isAuthenticated;
};

const shouldBypassAuth = () => {
  if (import.meta.env.VITE_E2E_BYPASS_AUTH === 'true') {
    return true;
  }
  if (typeof window !== 'undefined') {
    try {
      return window.localStorage.getItem('e2e_bypass_auth') === '1';
    } catch {
      return false;
    }
  }
  return false;
};

// Root route with layout
const rootRoute = createRootRoute({
  component: RootLayout,
});

// Public routes
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: lazyRouteComponent(() => import('@/pages/LandingPage')),
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: lazyRouteComponent(() => import('@/pages/LoginPage')),
});

// Weaver has its own layout (full-screen flow editor)
const weaverRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/weaver',
  component: lazyRouteComponent(() => import('@/pages/WeaverPage')),
});

// Protected layout route
const protectedLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'protected',
  beforeLoad: async () => {
    if (shouldBypassAuth()) {
      return;
    }
    const authStore = useAuthStore as AuthStoreWithPersist;
    if (authStore.persist && !authStore.persist.hasHydrated()) {
      await authStore.persist.rehydrate();
    }
    await useAuthStore.getState().initialize();
    if (!isAuthenticated()) {
      throw redirect({
        to: '/',
      });
    }
  },
  component: ProtectedLayout,
});

// Protected routes
const dashboardRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: '/dashboard',
  component: lazyRouteComponent(() => import('@/features/dashboard/DashboardPage')),
});

const charactersRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: '/characters',
  component: lazyRouteComponent(() => import('@/pages/CharactersPage')),
});

const campaignsRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: '/campaigns',
  component: lazyRouteComponent(() => import('@/pages/CampaignsPage')),
});

const storiesRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: '/stories',
  component: lazyRouteComponent(() => import('@/pages/StoriesPage')),
});

// Catch-all route
const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '*',
  beforeLoad: () => {
    throw redirect({
      to: '/',
    });
  },
});

// Route tree
const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  weaverRoute,
  protectedLayoutRoute.addChildren([
    dashboardRoute,
    charactersRoute,
    campaignsRoute,
    storiesRoute,
  ]),
  notFoundRoute,
]);

// Create router instance
export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,
});

// Type declaration for router
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
