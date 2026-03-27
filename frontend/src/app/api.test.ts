import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import { sessionStorageKey } from '@/shared/storage';

describe('api', () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('attaches the stored bearer token to story library requests', async () => {
    window.localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({
        kind: 'user',
        workspaceId: 'workspace-123',
        token: 'access-token-123',
        refreshToken: 'refresh-token-456',
        user: {
          id: 'user-123',
          name: 'Operator',
          email: 'operator@novel.engine',
        },
      }),
    );

    const response = new Response(
      JSON.stringify({
        stories: [],
        count: 0,
        limit: 20,
        offset: 0,
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);

    await api.listStories('workspace-123');

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/story?author_id=workspace-123&limit=20&offset=0',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer access-token-123',
        }),
      }),
    );
  });

  it('posts the full story pipeline payload to the canonical endpoint', async () => {
    const response = new Response(
      JSON.stringify({
        story: {
          id: 'story-1',
          title: 'Pipeline Story',
          genre: 'fantasy',
          author_id: 'workspace-123',
          status: 'active',
          chapters: [],
          chapter_count: 0,
          current_chapter_id: null,
          target_audience: null,
          themes: [],
          metadata: {},
          created_at: '2024-01-01T00:00:00.000Z',
          updated_at: '2024-01-01T00:00:00.000Z',
        },
        blueprint: {
          step: 'bible',
          provider: 'mock',
          model: 'deterministic-story-v1',
          generated_at: '2024-01-01T00:00:00.000Z',
          story_id: 'story-1',
          world_bible: {},
          character_bible: {},
          premise_summary: 'A premise',
        },
        outline: {
          step: 'outline',
          provider: 'mock',
          model: 'deterministic-story-v1',
          generated_at: '2024-01-01T00:00:00.000Z',
          target_chapters: 3,
          chapters: [],
        },
        drafted_chapters: 0,
        initial_review: {
          story_id: 'story-1',
          quality_score: 100,
          ready_for_publish: true,
          summary: 'Story passes the publication gate.',
          issues: [],
          revision_notes: [],
          chapter_count: 0,
          scene_count: 0,
          continuity_checks: {},
          checked_at: '2024-01-01T00:00:00.000Z',
        },
        revision_notes: [],
        final_review: {
          story_id: 'story-1',
          quality_score: 100,
          ready_for_publish: true,
          summary: 'Story passes the publication gate.',
          issues: [],
          revision_notes: [],
          chapter_count: 0,
          scene_count: 0,
          continuity_checks: {},
          checked_at: '2024-01-01T00:00:00.000Z',
        },
        export: {
          story: {
            id: 'story-1',
            title: 'Pipeline Story',
            genre: 'fantasy',
            author_id: 'workspace-123',
            status: 'active',
            chapters: [],
            chapter_count: 0,
            current_chapter_id: null,
            target_audience: null,
            themes: [],
            metadata: {},
            created_at: '2024-01-01T00:00:00.000Z',
            updated_at: '2024-01-01T00:00:00.000Z',
          },
          workflow: {},
          memory: {},
          blueprint: null,
          outline: null,
          last_review: null,
          revision_notes: [],
        },
        published: true,
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);

    await api.runPipeline({
      title: 'Pipeline Story',
      genre: 'fantasy',
      premise: 'A courier finds a map that rewrites the kingdom.',
      target_chapters: 3,
      author_id: 'workspace-123',
      publish: true,
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/story/pipeline',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          title: 'Pipeline Story',
          genre: 'fantasy',
          premise: 'A courier finds a map that rewrites the kingdom.',
          target_chapters: 3,
          author_id: 'workspace-123',
          publish: true,
        }),
      }),
    );
  });
});
