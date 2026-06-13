const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? '');
const apiTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT ?? '300000');

export const appConfig = {
  apiBaseUrl,
  apiTimeoutMs,
  endpoints: {
    setup: '/api/setup',
    session: '/api/session',
    projects: '/api/projects',
  },
} as const;
