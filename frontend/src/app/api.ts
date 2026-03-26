import { appConfig } from '@/app/config';
import type {
  DashboardStatus,
  GuestSessionResponse,
  LoginRequest,
  LoginResponse,
  OrchestrationStatus,
  SessionState,
} from '@/app/types';
import { sessionStorageKey, safeStorage } from '@/shared/storage';

class HttpError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const buildUrl = (path: string) =>
  appConfig.apiBaseUrl ? `${appConfig.apiBaseUrl}${path}` : path;

function getAuthorizationHeaders(): Record<string, string> {
  const session = safeStorage.read<SessionState>(sessionStorageKey);
  if (session?.kind === 'user' && session.token) {
    return { Authorization: `Bearer ${session.token}` };
  }

  return {};
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), appConfig.apiTimeoutMs);

  try {
    const response = await fetch(buildUrl(path), {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthorizationHeaders(),
        ...(init?.headers ?? {}),
      },
      ...init,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new HttpError(`Request failed with status ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export const api = {
  createGuestSession: () =>
    requestJson<GuestSessionResponse>(appConfig.endpoints.guestSession, { method: 'POST' }),

  login: (payload: LoginRequest) =>
    requestJson<LoginResponse>(appConfig.endpoints.login, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getDashboardStatus: (workspaceId: string) =>
    requestJson<DashboardStatus>(
      `${appConfig.endpoints.dashboardStatus}?workspace_id=${encodeURIComponent(workspaceId)}`,
    ),

  getOrchestrationStatus: (workspaceId: string) =>
    requestJson<OrchestrationStatus>(
      `${appConfig.endpoints.orchestrationStatus}?workspace_id=${encodeURIComponent(workspaceId)}`,
    ),

  startOrchestration: (workspaceId: string) =>
    requestJson<OrchestrationStatus>(appConfig.endpoints.orchestrationStart, {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),

  pauseOrchestration: (workspaceId: string) =>
    requestJson<OrchestrationStatus>(appConfig.endpoints.orchestrationPause, {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),

  stopOrchestration: (workspaceId: string) =>
    requestJson<OrchestrationStatus>(appConfig.endpoints.orchestrationStop, {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),
};
