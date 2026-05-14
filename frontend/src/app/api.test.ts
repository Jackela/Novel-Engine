import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';

describe('api', () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('uses cookie credentials without bearer tokens for story library requests', async () => {
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

    await api.listStories();

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/story?limit=20&offset=0',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      }),
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.headers).not.toHaveProperty('Authorization');
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

  it('maps gateway failures to a user-facing service unavailable message', async () => {
    const response = new Response('<html><body>bad gateway</body></html>', {
      status: 502,
      headers: {
        'Content-Type': 'text/html',
      },
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);

    await expect(api.createGuestSession()).rejects.toMatchObject({
      status: 502,
      message: 'Service temporarily unavailable. Start the backend API and retry.',
    });
  });

  it('maps aborted requests to a timeout message', async () => {
    const abortError = new Error('The operation was aborted.');
    abortError.name = 'AbortError';
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(abortError);

    await expect(api.createGuestSession()).rejects.toThrow(
      'Request timed out. Please retry.',
    );
  });

  it('maps network failures to a service unavailable message', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(api.createGuestSession()).rejects.toThrow(
      'Service temporarily unavailable. Start the backend API and retry.',
    );
  });

  it('uses browser cookies for current-user requests', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'user-1',
          username: 'operator',
          email: 'operator@novel.engine',
          roles: ['author'],
          is_active: true,
          created_at: '2024-01-01T00:00:00.000Z',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );

    await api.getCurrentUser();

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/auth/me',
      expect.objectContaining({
        credentials: 'include',
      }),
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.headers).not.toHaveProperty('Authorization');
  });

  it('builds story list query parameters with caller-provided pagination', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ stories: [], count: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await api.listStories(20, 10);

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/story?limit=20&offset=10',
      expect.any(Object),
    );
  });

  it('routes story workspace, run, artifact, and step requests to canonical endpoints', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await api.getStory('story-1');
    await api.getStoryWorkspace('story-1');
    await api.getStoryRuns('story-1');
    await api.getStoryRun('story-1', 'run-1');
    await api.getStoryArtifacts('story-1');
    await api.createStory({
      title: 'Story',
      genre: 'fantasy',
      premise: 'A platform test premise.',
      target_chapters: 3,
    });
    await api.generateBlueprint('story-1');
    await api.generateOutline('story-1');
    await api.draftStory('story-1');
    await api.draftStory('story-1', 4);
    await api.reviewStory('story-1');
    await api.reviseStory('story-1');
    await api.exportStory('story-1');
    await api.publishStory('story-1');

    expect(fetchSpy.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/story/story-1',
      '/api/v1/story/story-1/workspace',
      '/api/v1/story/story-1/runs',
      '/api/v1/story/story-1/runs/run-1',
      '/api/v1/story/story-1/artifacts',
      '/api/v1/story',
      '/api/v1/story/story-1/blueprint',
      '/api/v1/story/story-1/outline',
      '/api/v1/story/story-1/draft',
      '/api/v1/story/story-1/draft',
      '/api/v1/story/story-1/review',
      '/api/v1/story/story-1/revise',
      '/api/v1/story/story-1/export',
      '/api/v1/story/story-1/publish',
    ]);
    expect(fetchSpy.mock.calls[5]?.[1]).toEqual(
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          title: 'Story',
          genre: 'fantasy',
          premise: 'A platform test premise.',
          target_chapters: 3,
        }),
      }),
    );
    expect(fetchSpy.mock.calls[8]?.[1]).toEqual(
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({}),
      }),
    );
    expect(fetchSpy.mock.calls[9]?.[1]).toEqual(
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ target_chapters: 4 }),
      }),
    );
  });

  it('surfaces text error responses when they are not HTML', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('plain upstream failure', {
        status: 500,
        headers: { 'Content-Type': 'text/plain' },
      }),
    );

    await expect(api.createGuestSession()).rejects.toMatchObject({
      status: 500,
      message: 'plain upstream failure',
    });
  });

  it('uses detail and message fields from JSON error payloads', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Validation detail' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: 'Top-level message' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { detail: 'Nested detail' } }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }),
      );

    await expect(api.createGuestSession()).rejects.toMatchObject({
      status: 400,
      message: 'Validation detail',
    });
    await expect(api.createGuestSession()).rejects.toMatchObject({
      status: 409,
      message: 'Top-level message',
    });
    await expect(api.createGuestSession()).rejects.toMatchObject({
      status: 422,
      message: 'Nested detail',
    });
  });
});
