import { appConfig } from '@/app/config';
import type {
  CurrentUserResponse,
  GuestSessionRequest,
  GuestSessionResponse,
  LoginRequest,
  LoginResponse,
} from '@/app/types/auth';
import type {
  ProviderListResponse,
  WorkspaceCreateRequest,
  WorkspaceJob,
  WorkspaceJobRequest,
  WorkspaceListResponse,
  WorkspaceStatus,
} from '@/app/types/story';

class HttpError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const buildUrl = (path: string) =>
  appConfig.apiBaseUrl ? `${appConfig.apiBaseUrl}${path}` : path;

function fallbackErrorMessage(status: number): string {
  if (status === 502 || status === 503 || status === 504) {
    return 'Service temporarily unavailable. Start the backend API and retry.';
  }

  if (status === 408) {
    return 'Request timed out. Please retry.';
  }

  return `Request failed with status ${status}`;
}

function isLikelyHtml(payload: string): boolean {
  const normalized = payload.trim().toLowerCase();
  return normalized.startsWith('<!doctype html') || normalized.startsWith('<html');
}

function pickErrorMessage(payload: unknown): string | null {
  if (payload == null || typeof payload !== 'object' || Array.isArray(payload)) {
    return null;
  }

  const record = payload as Record<string, unknown>;
  const detail = record.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  const error = record.error;
  if (typeof error === 'string' && error.trim()) {
    return error;
  }
  if (error != null && typeof error === 'object' && !Array.isArray(error)) {
    const nestedMessage = (error as Record<string, unknown>).message;
    if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
      return nestedMessage;
    }

    const nestedDetail = (error as Record<string, unknown>).detail;
    if (typeof nestedDetail === 'string' && nestedDetail.trim()) {
      return nestedDetail;
    }
  }

  const message = record.message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  return null;
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const controller = new AbortController();
  const externalSignal = init?.signal;
  let timedOut = false;
  const abortFromExternal = () => controller.abort();
  if (externalSignal?.aborted) {
    controller.abort();
  } else {
    externalSignal?.addEventListener('abort', abortFromExternal, { once: true });
  }
  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, appConfig.apiTimeoutMs);

  try {
    let response: Response;
    try {
      response = await fetch(buildUrl(path), {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(init?.headers ?? {}),
        },
        ...init,
        signal: controller.signal,
      });
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(timedOut ? 'Request timed out. Please retry.' : 'Request cancelled.');
      }

      if (error instanceof TypeError) {
        throw new Error('Service temporarily unavailable. Start the backend API and retry.');
      }

      throw error;
    }

    if (!response.ok) {
      let message = fallbackErrorMessage(response.status);
      const contentType = response.headers.get('Content-Type') ?? '';

      if (contentType.includes('application/json')) {
        try {
          const payload = (await response.json()) as unknown;
          message = pickErrorMessage(payload) ?? message;
        } catch {
          // Fall back to the generic HTTP status message.
        }
      } else {
        try {
          const detail = (await response.text()).trim();
          if (detail && !isLikelyHtml(detail)) {
            message = detail;
          }
        } catch {
          // Fall back to the generic HTTP status message.
        }
      }

      throw new HttpError(message, response.status);
    }

    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeoutId);
    externalSignal?.removeEventListener('abort', abortFromExternal);
  }
}

export const api = {
  createGuestSession: (payload?: GuestSessionRequest) =>
    requestJson<GuestSessionResponse>(appConfig.endpoints.guestSession, {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    }),

  login: (payload: LoginRequest) =>
    requestJson<LoginResponse>(appConfig.endpoints.login, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  refreshSession: () =>
    requestJson<LoginResponse>(appConfig.endpoints.refresh, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  logout: () =>
    requestJson<{ message: string }>(appConfig.endpoints.logout, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  getCurrentUser: () =>
    requestJson<CurrentUserResponse>(appConfig.endpoints.currentUser),

  listProviders: (init?: RequestInit) =>
    requestJson<ProviderListResponse>(appConfig.endpoints.providers, init),

  listWorkspaces: (init?: RequestInit) =>
    requestJson<WorkspaceListResponse>(appConfig.endpoints.workspaces, init),

  createWorkspace: (payload: WorkspaceCreateRequest) =>
    requestJson<WorkspaceStatus>(appConfig.endpoints.workspaces, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getWorkspace: (workspaceId: string, init?: RequestInit) =>
    requestJson<WorkspaceStatus>(
      `${appConfig.endpoints.workspaces}/${encodeURIComponent(workspaceId)}`,
      init,
    ),

  createWorkspaceJob: (workspaceId: string, payload: WorkspaceJobRequest) =>
    requestJson<WorkspaceJob>(
      `${appConfig.endpoints.workspaces}/${encodeURIComponent(workspaceId)}/jobs`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    ),

  getWorkspaceJob: (workspaceId: string, jobId: string, init?: RequestInit) =>
    requestJson<WorkspaceJob>(
      `${appConfig.endpoints.workspaces}/${encodeURIComponent(
        workspaceId,
      )}/jobs/${encodeURIComponent(jobId)}`,
      init,
    ),
};
