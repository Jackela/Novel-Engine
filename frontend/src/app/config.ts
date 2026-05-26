const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? '');
const apiTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT ?? '300000');

export const appConfig = {
  apiBaseUrl,
  apiTimeoutMs,
  endpoints: {
    guestSession: '/api/guest/session',
    login: '/api/auth/login',
    logout: '/api/auth/logout',
    refresh: '/api/auth/refresh',
    currentUser: '/api/auth/me',
    providers: '/api/providers',
    workspaces: '/api/workspaces',
  },
} as const;
