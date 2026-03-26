const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? '');
const apiTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT ?? '10000');

export const appConfig = {
  apiBaseUrl,
  apiTimeoutMs,
  endpoints: {
    guestSession: '/api/v1/guest/session',
    login: '/api/v1/auth/login',
    dashboardStatus: '/api/v1/dashboard/status',
    orchestrationStatus: '/api/v1/dashboard/orchestration',
    orchestrationStart: '/api/v1/dashboard/orchestration/start',
    orchestrationPause: '/api/v1/dashboard/orchestration/pause',
    orchestrationStop: '/api/v1/dashboard/orchestration/stop',
    eventsStream: '/api/v1/dashboard/events/stream',
  },
} as const;
