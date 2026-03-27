const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? '');
const apiTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT ?? '10000');

export const appConfig = {
  apiBaseUrl,
  apiTimeoutMs,
  endpoints: {
    guestSession: '/api/v1/guest/session',
    login: '/api/v1/auth/login',
    story: '/api/v1/story',
    storyPipeline: '/api/v1/story/pipeline',
  },
} as const;
