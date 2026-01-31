/**
 * NarrativeSidebar - Outliner UI for story chapters and scenes.
 *
 * Why: Provides a tree-view navigation structure for the story outline,
 * allowing authors to quickly navigate between chapters and scenes while
 * maintaining context of the overall narrative structure.
 */
import { useState } from 'react';
import { ChevronRight, ChevronDown, FileText, FolderOpen } from 'lucide-react';

import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

/**
 * Scene data structure for the outliner.
 *
 * Why: Matches the backend SceneResponse schema to ensure type consistency
 * when real API integration is implemented in NAR-009.
 */
export interface OutlinerScene {
  id: string;
  chapter_id: string;
  title: string;
  order_index: number;
  status: 'draft' | 'generating' | 'review' | 'published';
}

/**
 * Chapter data structure for the outliner.
 *
 * Why: Matches the backend ChapterResponse schema with nested scenes
 * for hierarchical rendering in the sidebar.
 */
export interface OutlinerChapter {
  id: string;
  story_id: string;
  title: string;
  order_index: number;
  status: 'draft' | 'published';
  scenes: OutlinerScene[];
}

interface NarrativeSidebarProps {
  /** List of chapters with their nested scenes */
  chapters: OutlinerChapter[];
  /** Currently selected scene ID */
  activeSceneId?: string;
  /** Called when a scene is selected */
  onSceneSelect?: (sceneId: string, chapterId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Mock data for development and testing.
 *
 * Why: Enables UI development and testing before backend API integration,
 * following the PRD requirement for mock data rendering.
 */
export const MOCK_CHAPTERS: OutlinerChapter[] = [
  {
    id: 'chapter-1',
    story_id: 'story-1',
    title: 'Chapter 1: The Beginning',
    order_index: 0,
    status: 'published',
    scenes: [
      {
        id: 'scene-1-1',
        chapter_id: 'chapter-1',
        title: 'Opening Scene',
        order_index: 0,
        status: 'published',
      },
      {
        id: 'scene-1-2',
        chapter_id: 'chapter-1',
        title: 'First Encounter',
        order_index: 1,
        status: 'review',
      },
      {
        id: 'scene-1-3',
        chapter_id: 'chapter-1',
        title: 'The Decision',
        order_index: 2,
        status: 'draft',
      },
    ],
  },
  {
    id: 'chapter-2',
    story_id: 'story-1',
    title: 'Chapter 2: Rising Action',
    order_index: 1,
    status: 'draft',
    scenes: [
      {
        id: 'scene-2-1',
        chapter_id: 'chapter-2',
        title: 'Journey Begins',
        order_index: 0,
        status: 'generating',
      },
      {
        id: 'scene-2-2',
        chapter_id: 'chapter-2',
        title: 'Unexpected Ally',
        order_index: 1,
        status: 'draft',
      },
    ],
  },
  {
    id: 'chapter-3',
    story_id: 'story-1',
    title: 'Chapter 3: The Conflict',
    order_index: 2,
    status: 'draft',
    scenes: [
      {
        id: 'scene-3-1',
        chapter_id: 'chapter-3',
        title: 'Confrontation',
        order_index: 0,
        status: 'draft',
      },
    ],
  },
];

/**
 * Status badge component for visual status indication.
 *
 * Why: Provides at-a-glance status information using color coding,
 * helping authors quickly identify which scenes need attention.
 */
function StatusBadge({ status }: { status: OutlinerScene['status'] }) {
  const statusStyles: Record<OutlinerScene['status'], string> = {
    draft: 'bg-muted text-muted-foreground',
    generating: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    review: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    published: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  };

  return (
    <span
      className={cn(
        'ml-auto rounded px-1.5 py-0.5 text-xs font-medium',
        statusStyles[status]
      )}
    >
      {status}
    </span>
  );
}

/**
 * Chapter item component with collapsible scenes.
 *
 * Why: Implements a tree-view pattern common in writing applications,
 * allowing authors to expand/collapse chapters for better organization.
 */
function ChapterItem({
  chapter,
  activeSceneId,
  onSceneSelect,
}: {
  chapter: OutlinerChapter;
  activeSceneId: string | undefined;
  onSceneSelect: ((sceneId: string, chapterId: string) => void) | undefined;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasActiveScene = chapter.scenes.some((s) => s.id === activeSceneId);

  return (
    <div className="mb-1" data-testid={`chapter-item-${chapter.id}`}>
      {/* Chapter header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm font-medium',
          'hover:bg-accent hover:text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          hasActiveScene && 'text-primary'
        )}
        aria-expanded={isExpanded}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
        <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="truncate">{chapter.title}</span>
      </button>

      {/* Scenes list */}
      {isExpanded && (
        <div className="ml-4 border-l border-border pl-2">
          {chapter.scenes.map((scene) => (
            <SceneItem
              key={scene.id}
              scene={scene}
              isActive={scene.id === activeSceneId}
              onSelect={() => onSceneSelect?.(scene.id, chapter.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Scene item component with active state highlighting.
 *
 * Why: The active scene highlighting is a PRD requirement to help
 * authors maintain context of their current editing position.
 */
function SceneItem({
  scene,
  isActive,
  onSelect,
}: {
  scene: OutlinerScene;
  isActive: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm',
        'hover:bg-accent hover:text-accent-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isActive && 'bg-primary text-primary-foreground hover:bg-primary/90'
      )}
      data-testid={`scene-item-${scene.id}`}
      aria-current={isActive ? 'true' : undefined}
    >
      <FileText className="h-4 w-4 shrink-0" />
      <span className="truncate">{scene.title}</span>
      <StatusBadge status={scene.status} />
    </button>
  );
}

/**
 * NarrativeSidebar - Main outliner component for story navigation.
 *
 * Why: Provides the primary navigation interface for the narrative editor,
 * implementing a tree-view structure that matches common writing application
 * patterns (Scrivener, Ulysses, etc.).
 */
export function NarrativeSidebar({
  chapters,
  activeSceneId,
  onSceneSelect,
  className,
}: NarrativeSidebarProps) {
  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r border-border bg-background',
        className
      )}
      data-testid="narrative-sidebar"
    >
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Outline</h2>
        <p className="text-xs text-muted-foreground">
          {chapters.length} chapter{chapters.length !== 1 ? 's' : ''} ·{' '}
          {chapters.reduce((acc, ch) => acc + ch.scenes.length, 0)} scene
          {chapters.reduce((acc, ch) => acc + ch.scenes.length, 0) !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Scrollable content */}
      <ScrollArea className="flex-1">
        <nav className="p-2" role="navigation" aria-label="Story outline">
          {chapters.length === 0 ? (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">
              No chapters yet. Create your first chapter to get started.
            </p>
          ) : (
            chapters
              .sort((a, b) => a.order_index - b.order_index)
              .map((chapter) => (
                <ChapterItem
                  key={chapter.id}
                  chapter={chapter}
                  activeSceneId={activeSceneId}
                  onSceneSelect={onSceneSelect}
                />
              ))
          )}
        </nav>
      </ScrollArea>
    </aside>
  );
}

export default NarrativeSidebar;
