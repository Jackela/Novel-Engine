/**
 * NarrativeEditorLayout - Main layout component for the narrative writing interface.
 *
 * Why: Combines the NarrativeSidebar (20% width) and EditorComponent (80% width)
 * into a cohesive writing environment, following the PRD layout specifications.
 * Supports drag-and-drop character mentions from the World sidebar tab.
 * CHAR-038: Integrates quick character creation from @mention in editor.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { cn } from '@/lib/utils';
import { NarrativeSidebarWithTabs } from './NarrativeSidebarWithTabs';
import { MOCK_CHAPTERS } from './NarrativeSidebar';
import { EditorComponent, type CharacterMentionInsert } from './EditorComponent';
import { CharacterDragOverlay } from '@/components/editor/DraggableCharacterItem';
import type { CharacterDragData } from '@/components/editor/DraggableCharacterItem';
import { useStoryStructure } from '@/hooks/useStoryStructure';
import { moveScene } from '@/lib/api';
import type { OutlinerChapter, SceneMoveResult } from './NarrativeSidebar';
import { useCharacters } from '@/features/characters/api/characterApi';
import { ContextInspector } from './ContextInspector';

interface NarrativeEditorLayoutProps {
  /** Story ID to load (optional, loads from backend when provided) */
  storyId?: string;
  /** Story chapters data (optional, defaults to backend data or mock) */
  chapters?: OutlinerChapter[];
  /** Additional CSS classes for the container */
  className?: string;
  /** Use mock data instead of backend (defaults to false) */
  useMockData?: boolean;
}

/**
 * NarrativeEditorLayout - The main writing interface layout.
 *
 * Why: Provides a standard split-pane layout common in professional writing
 * applications (Scrivener, Ulysses), with the outline on the left for
 * navigation and the editor on the right for content creation.
 */
export function NarrativeEditorLayout({
  storyId,
  chapters: propChapters,
  className,
  useMockData = false,
}: NarrativeEditorLayoutProps) {
  // CHAR-038: Get characters list for @mention suggestions
  const { data: characters = [] } = useCharacters();
  const queryClient = useQueryClient();

  // BRAIN-036-02: Context Inspector state
  const [contextInspectorOpen, setContextInspectorOpen] = useState(false);

  // Load story structure from backend
  const {
    chapters: backendChapters,
    isLoading,
    error,
    loadStories,
  } = useStoryStructure(storyId);

  // Load stories on mount if not using mock data
  useEffect(() => {
    if (!useMockData && !storyId) {
      loadStories();
    }
  }, [useMockData, storyId, loadStories]);

  // Determine which chapters to use: props > backend > mock
  const chapters =
    propChapters ??
    (useMockData
      ? MOCK_CHAPTERS
      : backendChapters.length > 0
        ? backendChapters
        : MOCK_CHAPTERS);

  // Track active scene for sidebar highlighting and content loading
  const [activeSceneId, setActiveSceneId] = useState<string | undefined>(
    chapters[0]?.scenes[0]?.id
  );

  // Drag-and-drop state for character mentions
  const [activeDragData, setActiveDragData] = useState<CharacterDragData | null>(null);
  const [pendingMention, setPendingMention] = useState<CharacterMentionInsert | null>(
    null
  );
  const [isOverEditor, setIsOverEditor] = useState(false);

  // DnD sensors with higher distance threshold to avoid accidental drags
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 10,
      },
    })
  );

  // Update active scene when chapters change
  useEffect(() => {
    const firstChapter = chapters[0];
    const firstScene = firstChapter?.scenes[0];
    if (chapters.length > 0 && firstScene && !activeSceneId) {
      setActiveSceneId(firstScene.id);
    }
  }, [chapters, activeSceneId]);

  // Find the active scene's content (placeholder for now)
  const getSceneContent = (sceneId: string | undefined): string => {
    if (!sceneId) {
      return '<p>Select a scene from the outline to start writing...</p>';
    }
    // Find the scene in the chapters
    for (const chapter of chapters) {
      const scene = chapter.scenes.find((s) => s.id === sceneId);
      if (scene) {
        return `<h2>${scene.title}</h2><p>Start writing your scene content here...</p>`;
      }
    }
    return '<p>Scene not found</p>';
  };

  const handleSceneSelect = (sceneId: string, _chapterId: string) => {
    setActiveSceneId(sceneId);
  };

  const handleEditorChange = (html: string) => {
    // Future: Save content to backend via API
    console.log('Editor content changed:', html.substring(0, 100) + '...');
  };

  /**
   * Handle character drag start.
   *
   * Why: Track which character is being dragged to show the drag overlay
   * and enable the editor drop zone visual feedback.
   */
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const data = event.active.data.current as CharacterDragData | undefined;
    if (data?.type === 'character') {
      setActiveDragData(data);
    }
  }, []);

  /**
   * Handle drag end - insert character mention if dropped on editor.
   *
   * Why: When a character is dropped on the editor zone, we set the
   * pendingMention state which triggers the EditorComponent to insert
   * the @mention at the cursor position.
   */
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { over } = event;

      if (over?.id === 'editor-drop-zone' && activeDragData) {
        // Set pending mention to trigger insertion in EditorComponent
        setPendingMention({
          characterId: activeDragData.characterId,
          characterName: activeDragData.characterName,
        });
      }

      // Reset drag state
      setActiveDragData(null);
      setIsOverEditor(false);
    },
    [activeDragData]
  );

  /**
   * Handle drag over to show drop indicator on editor.
   */
  const handleDragOver = useCallback(
    (event: { over: { id: string | number } | null }) => {
      setIsOverEditor(event.over?.id === 'editor-drop-zone');
    },
    []
  );

  /**
   * Clear pending mention after it has been inserted.
   */
  const handleMentionInserted = useCallback(() => {
    setPendingMention(null);
  }, []);

  /**
   * CHAR-038: Handle character created from quick-create dialog.
   *
   * Why: When a new character is created via @mention, we need to refresh
   * the characters list so the sidebar and future suggestions show the new
   * character. The mention is inserted by EditorComponent after creation.
   */
  const handleCharacterCreated = useCallback(
    (_characterId: string, _characterName: string) => {
      // Invalidate characters query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['characters'] });
    },
    [queryClient]
  );

  /**
   * Handle scene move from drag-and-drop.
   *
   * Why: Persists scene reordering to the backend, enabling cross-chapter
   * scene movement as required by NAR-013.
   */
  const handleSceneMove = useCallback(
    async (result: SceneMoveResult) => {
      const { sceneId, sourceChapterId, targetChapterId, newOrderIndex } = result;

      // Get the current story ID
      const storyId = chapters[0]?.story_id;
      if (!storyId) {
        console.error('No story ID available for scene move');
        return;
      }

      try {
        // Call the backend API to move the scene
        await moveScene(
          storyId,
          sourceChapterId,
          sceneId,
          newOrderIndex,
          sourceChapterId !== targetChapterId ? targetChapterId : undefined
        );

        // Refresh the structure to reflect the changes
        if (!useMockData) {
          loadStories();
        }

        console.log(
          `Moved scene ${sceneId} from ${sourceChapterId} to ${targetChapterId} at index ${newOrderIndex}`
        );
      } catch (error) {
        console.error('Failed to move scene:', error);
        toast.error('Failed to move scene. Please try again.');
      }
    },
    [chapters, useMockData, loadStories]
  );

  // Show loading state
  if (isLoading && !useMockData) {
    return (
      <div
        className={cn('flex h-full w-full items-center justify-center', className)}
        data-testid="narrative-editor-layout"
      >
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p>Loading story structure...</p>
        </div>
      </div>
    );
  }

  // Show error state (but still allow fallback to mock)
  if (error && !useMockData && chapters.length === 0) {
    return (
      <div
        className={cn('flex h-full w-full items-center justify-center', className)}
        data-testid="narrative-editor-layout"
      >
        <div className="flex flex-col items-center gap-2 text-destructive">
          <p>Failed to load story: {error}</p>
          <button
            type="button"
            onClick={() => loadStories()}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
    >
      <div
        className={cn('flex h-full w-full overflow-hidden', className)}
        data-testid="narrative-editor-layout"
      >
        {/* Sidebar - 20% width */}
        <div className="w-1/5 min-w-[200px] max-w-[300px] shrink-0">
          <NarrativeSidebarWithTabs
            chapters={chapters}
            activeSceneId={activeSceneId}
            onSceneSelect={handleSceneSelect}
            onSceneMove={handleSceneMove}
            className="h-full"
          />
        </div>

        {/* Editor - 80% width (remaining space) */}
        <main className="flex flex-1 flex-col overflow-hidden bg-background p-4">
          <EditorComponent
            initialContent={getSceneContent(activeSceneId)}
            onChange={handleEditorChange}
            className="h-full"
            sceneId={activeSceneId}
            isDropTarget={isOverEditor}
            pendingMention={pendingMention}
            onMentionInserted={handleMentionInserted}
            characters={characters}
            onCharacterCreated={handleCharacterCreated}
            ragEnabled={true}
            onViewAIContext={() => setContextInspectorOpen(true)}
          />
        </main>

        {/* BRAIN-036-02: Context Inspector Panel */}
        <ContextInspector
          open={contextInspectorOpen}
          onClose={() => setContextInspectorOpen(false)}
          query={getSceneContent(activeSceneId)}
          {...(activeSceneId && { sceneId: activeSceneId })}
        />

        {/* Drag overlay for character being dragged */}
        <DragOverlay>
          {activeDragData ? (
            <CharacterDragOverlay name={activeDragData.characterName} />
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
}

export default NarrativeEditorLayout;
