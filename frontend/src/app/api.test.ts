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
          version: 1,
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
          version: 1,
          chapters: [],
        },
        drafted_chapters: 0,
        initial_review: {
          artifact_id: 'review-1',
          version: 1,
          source_run_id: 'run-1',
          source_provider: 'system',
          source_model: 'continuity-review-v1',
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
          metrics: {
            continuity_score: 100,
            pacing_score: 100,
            hook_score: 100,
            character_consistency_score: 100,
            timeline_consistency_score: 100,
          },
        },
        revision_notes: [],
        final_review: {
          artifact_id: 'review-2',
          version: 2,
          source_run_id: 'run-1',
          source_provider: 'system',
          source_model: 'continuity-review-v1',
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
          metrics: {
            continuity_score: 100,
            pacing_score: 100,
            hook_score: 100,
            character_consistency_score: 100,
            timeline_consistency_score: 100,
          },
        },
        export: {
          artifact_id: 'export-1',
          version: 1,
          source_run_id: 'run-1',
          source_provider: 'system',
          source_model: 'workspace-export-v1',
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
          exported_at: '2024-01-01T00:00:00.000Z',
        },
        workspace: {
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
          workflow: {
            schema_version: 1,
            status: 'published',
            premise: 'A premise',
            tone: 'commercial web fiction',
            target_chapters: 3,
            generation_trace: [],
            chapter_memory: [],
            revision_notes: [],
            blueprint: null,
            blueprint_generated_at: null,
            outline: null,
            outline_generated_at: null,
            drafted_chapters: 0,
            last_review: null,
            last_exported_at: null,
            last_updated_at: '2024-01-01T00:00:00.000Z',
            published_at: '2024-01-01T00:00:00.000Z',
            revision_history: [],
            run_state: null,
            current_run_id: null,
          },
          memory: {
            schema_version: 1,
            premise: 'A premise',
            tone: 'commercial web fiction',
            target_chapters: 3,
            themes: [],
            chapter_summaries: [],
            active_characters: [],
            outline_titles: [],
            timeline_ledger: [],
            hook_ledger: [],
            character_states: [],
            relationship_states: [],
            world_rules: [],
            revision_notes: [],
          },
          blueprint: null,
          outline: null,
          review: null,
          export: null,
          revision_notes: [],
          run: null,
          run_history: [],
          run_events: [],
          artifact_history: [],
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

  it('posts a run resource payload for an existing story', async () => {
    const response = new Response(
      JSON.stringify({
        operation: 'pipeline',
        story: {
          id: 'story-1',
          title: 'Run Story',
          genre: 'fantasy',
          author_id: 'workspace-123',
          status: 'draft',
          chapters: [],
          chapter_count: 0,
          current_chapter_id: null,
          target_audience: null,
          themes: [],
          metadata: {},
          created_at: '2024-01-01T00:00:00.000Z',
          updated_at: '2024-01-01T00:00:00.000Z',
        },
        workspace: {
          story: {
            id: 'story-1',
            title: 'Run Story',
            genre: 'fantasy',
            author_id: 'workspace-123',
            status: 'draft',
            chapters: [],
            chapter_count: 0,
            current_chapter_id: null,
            target_audience: null,
            themes: [],
            metadata: {},
            created_at: '2024-01-01T00:00:00.000Z',
            updated_at: '2024-01-01T00:00:00.000Z',
          },
          workflow: {
            schema_version: 1,
            status: 'drafted',
            premise: 'A premise',
            tone: 'commercial web fiction',
            target_chapters: 3,
            generation_trace: [],
            chapter_memory: [],
            revision_notes: [],
            blueprint: null,
            blueprint_generated_at: null,
            outline: null,
            outline_generated_at: null,
            drafted_chapters: 0,
            last_review: null,
            last_exported_at: null,
            last_updated_at: '2024-01-01T00:00:00.000Z',
            published_at: null,
            revision_history: [],
            run_state: null,
            current_run_id: null,
          },
          memory: {
            schema_version: 1,
            premise: 'A premise',
            tone: 'commercial web fiction',
            target_chapters: 3,
            themes: [],
            chapter_summaries: [],
            active_characters: [],
            outline_titles: [],
            timeline_ledger: [],
            hook_ledger: [],
            character_states: [],
            relationship_states: [],
            world_rules: [],
            revision_notes: [],
          },
          blueprint: null,
          outline: null,
          review: null,
          export: null,
          revision_notes: [],
          run: null,
          run_history: [],
          run_events: [],
          artifact_history: [],
        },
        run: {
          run_id: 'run-1',
          mode: 'pipeline',
          status: 'completed',
          started_at: '2024-01-01T00:00:00.000Z',
          completed_at: '2024-01-01T00:00:00.000Z',
          published: false,
          stages: [],
        },
        events: [],
        artifacts: [],
        latest_snapshot: null,
        stage_snapshots: [],
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);

    await api.createStoryRun('story-1', {
      operation: 'pipeline',
      target_chapters: 3,
      publish: false,
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/story/story-1/runs',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          operation: 'pipeline',
          target_chapters: 3,
          publish: false,
        }),
      }),
    );
  });

  it('surfaces API error details for failed login requests', async () => {
    const response = new Response(
      JSON.stringify({
        error: {
          code: 'HTTP_ERROR',
          message: 'Invalid credentials',
        },
      }),
      {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);

    await expect(
      api.login({
        email: 'operator@novel.engine',
        password: 'wrong-password',
      }),
    ).rejects.toMatchObject({
      status: 401,
      message: 'Invalid credentials',
    });
  });
});
