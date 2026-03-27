import { appConfig } from '@/app/config';
import type {
  StoryBlueprintResponse,
  StoryCreateRequest,
  StoryCreateResponse,
  StoryDraftResponse,
  StoryExportResponse,
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
  SessionState,
  StorySnapshot,
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

  listStories: (authorId: string, limit = 20, offset = 0) =>
    requestJson<StoryListResponse>(
      `${appConfig.endpoints.story}${buildStoryQuery({
        author_id: authorId,
        limit,
        offset,
      })}`,
    ),

  getStory: (storyId: string) =>
    requestJson<{ story: StorySnapshot }>(`${appConfig.endpoints.story}/${storyId}`),

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
