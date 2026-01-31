/**
 * NarrativeSidebar - Outliner UI for story chapters and scenes with drag-and-drop reordering.
 *
 * Why: Provides a tree-view navigation structure for the story outline,
 * allowing authors to quickly navigate between chapters and scenes while
 * maintaining context of the overall narrative structure. Supports drag-and-drop
 * reordering of scenes within and between chapters.
 */
import { useState, useCallback } from 'react';
import { ChevronRight, ChevronDown, FileText, FolderOpen, GripVertical } from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

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

/**
 * Result of a scene move operation.
 *
 * Why: Provides the necessary information for the parent component
 * to call the backend API to persist the reorder.
 */
export interface SceneMoveResult {
  sceneId: string;
  sourceChapterId: string;
  targetChapterId: string;
  newOrderIndex: number;
}

interface NarrativeSidebarProps {
  /** List of chapters with their nested scenes */
  chapters: OutlinerChapter[];
  /** Currently selected scene ID */
  activeSceneId?: string | undefined;
  /** Called when a scene is selected */
  onSceneSelect?: ((sceneId: string, chapterId: string) => void) | undefined;
  /** Called when a scene is moved (for API integration) */
  onSceneMove?: ((result: SceneMoveResult) => void) | undefined;
  /** Additional CSS classes */
  className?: string | undefined;
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
 * Sortable scene item component with drag handle.
 *
 * Why: Enables drag-and-drop reordering of scenes within the outliner,
 * a key UX requirement for efficient story organization.
 */
function SortableSceneItem({
  scene,
  isActive,
  onSelect,
}: {
  scene: OutlinerScene;
  isActive: boolean;
  onSelect: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: scene.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group flex items-center rounded-md',
        isDragging && 'opacity-50'
      )}
      data-testid={`scene-item-${scene.id}`}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="flex h-8 w-6 cursor-grab items-center justify-center opacity-0 transition-opacity group-hover:opacity-100"
        data-testid={`scene-drag-handle-${scene.id}`}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* Scene button */}
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          'flex flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm',
          'hover:bg-accent hover:text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          isActive && 'bg-primary text-primary-foreground hover:bg-primary/90'
        )}
        aria-current={isActive ? 'true' : undefined}
      >
        <FileText className="h-4 w-4 shrink-0" />
        <span className="truncate">{scene.title}</span>
        <StatusBadge status={scene.status} />
      </button>
    </div>
  );
}

/**
 * Static scene item for drag overlay.
 *
 * Why: Shows a visual representation of the scene being dragged,
 * providing clear feedback during the drag operation.
 */
function SceneOverlay({ scene }: { scene: OutlinerScene }) {
  return (
    <div className="flex items-center rounded-md border border-primary bg-background px-2 py-1.5 shadow-lg">
      <FileText className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="truncate text-sm">{scene.title}</span>
      <StatusBadge status={scene.status} />
    </div>
  );
}

/**
 * Chapter item component with collapsible scenes and drop zone.
 *
 * Why: Implements a tree-view pattern common in writing applications,
 * allowing authors to expand/collapse chapters for better organization.
 */
function ChapterItem({
  chapter,
  activeSceneId,
  onSceneSelect,
  isDropTarget,
}: {
  chapter: OutlinerChapter;
  activeSceneId: string | undefined;
  onSceneSelect: ((sceneId: string, chapterId: string) => void) | undefined;
  isDropTarget: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasActiveScene = chapter.scenes.some((s) => s.id === activeSceneId);

  const sceneIds = chapter.scenes.map((s) => s.id);

  return (
    <div
      className={cn('mb-1', isDropTarget && 'rounded-md ring-2 ring-primary')}
      data-testid={`chapter-item-${chapter.id}`}
      data-chapter-id={chapter.id}
    >
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

      {/* Scenes list with sortable context */}
      {isExpanded && (
        <div
          className="ml-4 border-l border-border pl-2"
          data-testid={`chapter-scenes-${chapter.id}`}
        >
          <SortableContext items={sceneIds} strategy={verticalListSortingStrategy}>
            {chapter.scenes
              .sort((a, b) => a.order_index - b.order_index)
              .map((scene) => (
                <SortableSceneItem
                  key={scene.id}
                  scene={scene}
                  isActive={scene.id === activeSceneId}
                  onSelect={() => onSceneSelect?.(scene.id, chapter.id)}
                />
              ))}
          </SortableContext>
          {chapter.scenes.length === 0 && (
            <div className="px-2 py-2 text-xs text-muted-foreground">
              No scenes. Drag one here.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * NarrativeSidebar - Main outliner component for story navigation with drag-and-drop.
 *
 * Why: Provides the primary navigation interface for the narrative editor,
 * implementing a tree-view structure that matches common writing application
 * patterns (Scrivener, Ulysses, etc.) with drag-and-drop scene reordering.
 */
export function NarrativeSidebar({
  chapters,
  activeSceneId,
  onSceneSelect,
  onSceneMove,
  className,
}: NarrativeSidebarProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overChapterId, setOverChapterId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  /**
   * Find which chapter a scene belongs to.
   */
  const findChapterForScene = useCallback(
    (sceneId: string): OutlinerChapter | undefined => {
      return chapters.find((ch) => ch.scenes.some((s) => s.id === sceneId));
    },
    [chapters]
  );

  /**
   * Find a scene by ID.
   */
  const findScene = useCallback(
    (sceneId: string): OutlinerScene | undefined => {
      for (const chapter of chapters) {
        const scene = chapter.scenes.find((s) => s.id === sceneId);
        if (scene) return scene;
      }
      return undefined;
    },
    [chapters]
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;

    if (!over) {
      setOverChapterId(null);
      return;
    }

    // Check if hovering over a chapter's drop zone
    const overId = over.id as string;
    const overChapter = chapters.find((ch) => ch.id === overId);

    if (overChapter) {
      setOverChapterId(overChapter.id);
      return;
    }

    // Check if hovering over another scene (find its chapter)
    const overSceneChapter = findChapterForScene(overId);
    if (overSceneChapter) {
      setOverChapterId(overSceneChapter.id);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setOverChapterId(null);

    if (!over) return;

    const activeSceneId = active.id as string;
    const overId = over.id as string;

    const sourceChapter = findChapterForScene(activeSceneId);
    if (!sourceChapter) return;

    // Determine target chapter and position
    let targetChapter: OutlinerChapter | undefined;
    let newOrderIndex: number;

    // Check if dropped on a chapter directly
    const droppedOnChapter = chapters.find((ch) => ch.id === overId);
    if (droppedOnChapter) {
      targetChapter = droppedOnChapter;
      newOrderIndex = targetChapter.scenes.length;
    } else {
      // Dropped on another scene
      targetChapter = findChapterForScene(overId);
      if (!targetChapter) return;

      const overScene = targetChapter.scenes.find((s) => s.id === overId);
      if (overScene) {
        newOrderIndex = overScene.order_index;
      } else {
        newOrderIndex = targetChapter.scenes.length;
      }
    }

    // No-op if dropping on same position
    if (
      sourceChapter.id === targetChapter.id &&
      active.id === over.id
    ) {
      return;
    }

    // Call the move callback
    onSceneMove?.({
      sceneId: activeSceneId,
      sourceChapterId: sourceChapter.id,
      targetChapterId: targetChapter.id,
      newOrderIndex,
    });
  };

  const activeScene = activeId ? findScene(activeId) : undefined;

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

      {/* Scrollable content with DnD context */}
      <ScrollArea className="flex-1">
        <nav className="p-2" role="navigation" aria-label="Story outline">
          {chapters.length === 0 ? (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">
              No chapters yet. Create your first chapter to get started.
            </p>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDragEnd={handleDragEnd}
            >
              {chapters
                .sort((a, b) => a.order_index - b.order_index)
                .map((chapter) => (
                  <ChapterItem
                    key={chapter.id}
                    chapter={chapter}
                    activeSceneId={activeSceneId}
                    onSceneSelect={onSceneSelect}
                    isDropTarget={overChapterId === chapter.id}
                  />
                ))}

              <DragOverlay>
                {activeScene ? <SceneOverlay scene={activeScene} /> : null}
              </DragOverlay>
            </DndContext>
          )}
        </nav>
      </ScrollArea>
    </aside>
  );
}

export default NarrativeSidebar;
