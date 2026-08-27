import { describe, expect, it } from 'vitest';

import type { Project, StudioDocument, Volume } from '@/app/types/studio';

import { needsGeneration, readingOrderChapters, wholeBookPlan } from './wholeBookPlan';

function chapter(input: Partial<StudioDocument> & { id: string }): StudioDocument {
  return {
    project_id: 'project-1',
    kind: 'chapter',
    title: `Chapter ${input.id}`,
    position: 0,
    volume_id: 'volume-1',
    current_revision_id: `revision-${input.id}`,
    content_markdown: '',
    metadata: {},
    revision_source: 'author',
    word_count: 0,
    created_at: '2026-08-27T00:00:00Z',
    updated_at: '2026-08-27T00:00:00Z',
    ...input,
  };
}

function volume(id: string, position: number): Volume {
  return {
    id,
    project_id: 'project-1',
    title: id,
    position,
    created_at: '2026-08-27T00:00:00Z',
    updated_at: '2026-08-27T00:00:00Z',
  };
}

const baseProject: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: '',
  settings: {},
  import_hash: null,
  created_at: '2026-08-27T00:00:00Z',
  updated_at: '2026-08-27T00:00:00Z',
};

describe('needsGeneration (#318 rule)', () => {
  it('regenerates every revision source except the accepted AI one', () => {
    expect(needsGeneration(chapter({ id: 'a', revision_source: 'author' }))).toBe(true);
    expect(needsGeneration(chapter({ id: 'b', revision_source: 'restore' }))).toBe(true);
    expect(needsGeneration(chapter({ id: 'c', revision_source: 'ai-accepted' }))).toBe(false);
  });
});

describe('readingOrderChapters (ADR-0005)', () => {
  it('orders by volume position first, then in-volume chapter position', () => {
    const project = {
      ...baseProject,
      volumes: [volume('volume-2', 1), volume('volume-1', 0)],
      documents: [
        chapter({ id: 'late', volume_id: 'volume-2', position: 1 }),
        chapter({ id: 'first-b', volume_id: 'volume-1', position: 1 }),
        chapter({ id: 'first-a', volume_id: 'volume-1', position: 0 }),
        chapter({ id: 'outline-doc', kind: 'outline', volume_id: null, position: 99 }),
        chapter({ id: 'late-a', volume_id: 'volume-2', position: 0 }),
      ],
    };
    expect(readingOrderChapters(project).map((document) => document.id)).toEqual([
      'first-a',
      'first-b',
      'late-a',
      'late',
    ]);
  });

  it('falls back to the first volume for chapters without a link', () => {
    const project = {
      ...baseProject,
      volumes: [volume('volume-late', 1), volume('volume-first', 0)],
      documents: [
        chapter({ id: 'linked', volume_id: 'volume-late', position: 0 }),
        chapter({ id: 'unlinked', volume_id: null, position: 50 }),
      ],
    };
    expect(readingOrderChapters(project).map((document) => document.id)).toEqual([
      'unlinked',
      'linked',
    ]);
  });

  it('does not mutate the project document list', () => {
    const documents = [chapter({ id: 'b', position: 1 }), chapter({ id: 'a', position: 0 })];
    const project = { ...baseProject, documents };
    readingOrderChapters(project);
    expect(documents.map((document) => document.id)).toEqual(['b', 'a']);
  });
});

describe('wholeBookPlan', () => {
  it('skips accepted AI revisions and keeps reading order', () => {
    const project = {
      ...baseProject,
      volumes: [volume('volume-1', 0)],
      documents: [
        chapter({ id: 'one', position: 0 }),
        chapter({ id: 'two', position: 1, revision_source: 'ai-accepted' }),
        chapter({ id: 'three', position: 2 }),
      ],
    };
    expect(wholeBookPlan(project)).toEqual([
      { id: 'one', title: 'Chapter one' },
      { id: 'three', title: 'Chapter three' },
    ]);
  });

  it('is empty when every chapter already carries an accepted AI revision', () => {
    const project = {
      ...baseProject,
      volumes: [volume('volume-1', 0)],
      documents: [chapter({ id: 'one', revision_source: 'ai-accepted' })],
    };
    expect(wholeBookPlan(project)).toEqual([]);
  });
});
