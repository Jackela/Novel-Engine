import { afterEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';

import { api } from '@/app/api';

import { render, screen, waitFor } from '../../../tests/test-utils';
import { useStoryWorkbench } from './useStoryWorkbench';
import type { StoryPipelineResult, StorySnapshot } from '@/app/types';

function makeStory(title: string, status: StorySnapshot['status'] = 'draft'): StorySnapshot {
  return {
    id: `${title.toLowerCase().replace(/\s+/g, '-')}-id`,
    title,
    genre: 'fantasy',
    author_id: 'workspace-123',
    status,
    chapters: [],
    chapter_count: 0,
    current_chapter_id: null,
    target_audience: null,
    themes: [],
    metadata: {},
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-01T00:00:00.000Z',
  };
}

function makePipelineResult(title: string): StoryPipelineResult {
  const story = {
    ...makeStory(title, 'active'),
    chapter_count: 3,
    chapters: [
      {
        id: 'chapter-1',
        story_id: `${title.toLowerCase().replace(/\s+/g, '-')}-id`,
        chapter_number: 1,
        title: 'Chapter 1',
        summary: 'Opening tension',
        scenes: [],
        metadata: {},
        created_at: '2024-01-01T00:00:00.000Z',
        updated_at: '2024-01-01T00:00:00.000Z',
      },
    ],
    metadata: {
      workflow: {
        status: 'published',
        target_chapters: 3,
        blueprint: {
          step: 'bible',
          provider: 'mock',
          model: 'deterministic-story-v1',
          generated_at: '2024-01-01T00:00:00.000Z',
          story_id: `${title.toLowerCase().replace(/\s+/g, '-')}-id`,
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
        revision_notes: ['Repaired the hook'],
        last_review: {
          story_id: `${title.toLowerCase().replace(/\s+/g, '-')}-id`,
          quality_score: 100,
          ready_for_publish: true,
          summary: 'Story passes the publication gate.',
          issues: [],
          revision_notes: ['Repaired the hook'],
          chapter_count: 3,
          scene_count: 1,
          continuity_checks: {},
          checked_at: '2024-01-01T00:00:00.000Z',
        },
      },
    },
    updated_at: '2024-01-01T00:00:00.000Z',
  };

  return {
    story,
    blueprint: story.metadata.workflow!.blueprint!,
    outline: story.metadata.workflow!.outline!,
    drafted_chapters: 3,
    initial_review: story.metadata.workflow!.last_review!,
    revision_notes: ['Repaired the hook'],
    final_review: story.metadata.workflow!.last_review!,
    export: {
      story,
      workflow: story.metadata.workflow!,
      memory: {},
      blueprint: null,
      outline: null,
      last_review: null,
      revision_notes: ['Repaired the hook'],
    },
    published: true,
  };
}

function StoryWorkbenchProbe({ authorId }: { authorId: string }) {
  const { stories, activeStory, artifact, createStory, runPipeline } = useStoryWorkbench(authorId);

  return (
    <div>
      <span data-testid="story-count">{stories.length}</span>
      <span data-testid="story-title">{activeStory?.title ?? 'none'}</span>
      <span data-testid="story-action">{artifact.lastAction ?? 'none'}</span>
      <button
        data-testid="create-story"
        onClick={() =>
          void createStory({
            title: 'Hook Story',
            genre: 'fantasy',
            premise: 'A courier maps a city that keeps moving at dawn.',
            target_chapters: 3,
            author_id: authorId,
          })
        }
        type="button"
      >
        Create
      </button>
      <button
        data-testid="run-pipeline"
        onClick={() =>
          void runPipeline({
            title: 'Pipeline Hook Story',
            genre: 'fantasy',
            premise: 'A courier maps a city that keeps moving at dawn.',
            target_chapters: 3,
            author_id: authorId,
            publish: true,
          })
        }
        type="button"
      >
        Pipeline
      </button>
    </div>
  );
}

describe('useStoryWorkbench', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates a story and runs the pipeline using the canonical author id', async () => {
    vi.spyOn(api, 'listStories').mockResolvedValue({
      stories: [],
      count: 0,
      limit: 20,
      offset: 0,
    });
    vi.spyOn(api, 'createStory').mockResolvedValue({
      story: makeStory('Hook Story'),
    });
    vi.spyOn(api, 'runPipeline').mockResolvedValue(makePipelineResult('Pipeline Hook Story'));

    render(<StoryWorkbenchProbe authorId="workspace-123" />);

    await waitFor(() => {
      expect(screen.getByTestId('story-count')).toHaveTextContent('0');
    });

    await act(async () => {
      screen.getByTestId('create-story').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('story-title')).toHaveTextContent('Hook Story');
      expect(screen.getByTestId('story-action')).toHaveTextContent('Created draft manuscript');
    });

    await act(async () => {
      screen.getByTestId('run-pipeline').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('story-title')).toHaveTextContent('Pipeline Hook Story');
      expect(screen.getByTestId('story-action')).toHaveTextContent(
        'Completed pipeline and published story',
      );
    });
  });
});
