import { appConfig } from '@/app/config';
import type {
  CurrentUserResponse,
  StoryBlueprintResponse,
  StoryCreateRequest,
  StoryCreateResponse,
  StoryDraftResponse,
  StoryExportResponse,
  GuestSessionRequest,
  GuestSessionResponse,
  LoginRequest,
  LoginResponse,
  StoryListResponse,
  StoryOutlineResponse,
  StoryPipelineRequest,
  StoryPipelineResult,
  StoryPublishResponse,
  StoryReviewResponse,
  StoryReviseResponse,
  StoryRunDetailResponse,
  StoryRunRequest,
  StoryRunsResponse,
  StoryArtifactsResponse,
  SessionState,
  StorySnapshot,
  StoryWorkspaceResponse,
} from '@/app/types';
import {
  getActiveSession,
  readSessionCatalog,
} from '@/shared/storage';

class HttpError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const buildUrl = (path: string) =>
  appConfig.apiBaseUrl ? `${appConfig.apiBaseUrl}${path}` : path;

function buildStoryQuery(params: Record<string, string | number | undefined>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }

    searchParams.set(key, String(value));
  }

  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

function getAuthorizationHeaders(token?: string): Record<string, string> {
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }

  const session = getActiveSession(readSessionCatalog());
  if (session?.kind === 'user' && session.token) {
    return { Authorization: `Bearer ${session.token}` };
  }

  return {};
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
  options?: { token?: string },
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), appConfig.apiTimeoutMs);

  try {
    const response = await fetch(buildUrl(path), {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthorizationHeaders(options?.token),
        ...(init?.headers ?? {}),
      },
      ...init,
      signal: controller.signal,
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
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
          if (detail) {
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

  getCurrentUser: (token?: string) =>
    requestJson<CurrentUserResponse>(
      appConfig.endpoints.currentUser,
      undefined,
      token ? { token } : undefined,
    ),

  listStories: (authorId: string, limit = 20, offset = 0) =>
    requestJson<StoryListResponse>(
      `${appConfig.endpoints.story}${buildStoryQuery({
        author_id: authorId,
        limit,
        offset,
      })}`,
    ),

  getStory: (storyId: string) =>
    requestJson<{ story: StorySnapshot; workspace: StoryWorkspaceResponse['workspace'] }>(
      `${appConfig.endpoints.story}/${storyId}`,
    ),

  getStoryWorkspace: (storyId: string) =>
    requestJson<StoryWorkspaceResponse>(
      `${appConfig.endpoints.story}/${storyId}/workspace`,
    ),

  getStoryRuns: (storyId: string) =>
    requestJson<StoryRunsResponse>(`${appConfig.endpoints.story}/${storyId}/runs`),

  getStoryRun: (storyId: string, runId: string) =>
    requestJson<StoryRunDetailResponse>(`${appConfig.endpoints.story}/${storyId}/runs/${runId}`),

  getStoryArtifacts: (storyId: string) =>
    requestJson<StoryArtifactsResponse>(`${appConfig.endpoints.story}/${storyId}/artifacts`),

  createStoryRun: (storyId: string, payload: StoryRunRequest) =>
    requestJson<StoryRunDetailResponse>(`${appConfig.endpoints.story}/${storyId}/runs`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  createStory: (payload: StoryCreateRequest) =>
    requestJson<StoryCreateResponse>(appConfig.endpoints.story, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  generateBlueprint: (storyId: string) =>
    requestJson<StoryBlueprintResponse>(`${appConfig.endpoints.story}/${storyId}/blueprint`, {
      method: 'POST',
    }),

  generateOutline: (storyId: string) =>
    requestJson<StoryOutlineResponse>(`${appConfig.endpoints.story}/${storyId}/outline`, {
      method: 'POST',
    }),

  draftStory: (storyId: string, targetChapters?: number | null) =>
    requestJson<StoryDraftResponse>(`${appConfig.endpoints.story}/${storyId}/draft`, {
      method: 'POST',
      body: JSON.stringify(
        targetChapters == null ? {} : { target_chapters: targetChapters },
      ),
    }),

  reviewStory: (storyId: string) =>
    requestJson<StoryReviewResponse>(`${appConfig.endpoints.story}/${storyId}/review`, {
      method: 'POST',
    }),

  reviseStory: (storyId: string) =>
    requestJson<StoryReviseResponse>(`${appConfig.endpoints.story}/${storyId}/revise`, {
      method: 'POST',
    }),

  exportStory: (storyId: string) =>
    requestJson<StoryExportResponse>(`${appConfig.endpoints.story}/${storyId}/export`, {
      method: 'POST',
    }),

  publishStory: (storyId: string) =>
    requestJson<StoryPublishResponse>(`${appConfig.endpoints.story}/${storyId}/publish`, {
      method: 'POST',
    }),

  runPipeline: (payload: StoryPipelineRequest) =>
    requestJson<StoryPipelineResult>(appConfig.endpoints.storyPipeline, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
