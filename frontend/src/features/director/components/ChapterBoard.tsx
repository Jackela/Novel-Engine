/**
 * ChapterBoard - Kanban-style scene organization by story beats.
 *
 * Why: Visualizes scene distribution across story structure phases (Setup,
 * Inciting Incident, Rising Action, Climax, Resolution). Enables drag-and-drop
 * reorganization to balance narrative pacing and ensure proper story arc.
 */
import { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, LayoutList, LayoutGrid } from 'lucide-react';

import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useScenes, useUpdateScenePhase } from '../api/sceneApi';
import type { SceneResponse, StoryPhase } from '@/types/schemas';

/**
 * Story phase configuration for Kanban columns.
 */
const STORY_PHASES: Array<{
  value: StoryPhase;
  label: string;
  description: string;
  color: string;
}> = [
  {
    value: 'setup',
    label: 'Setup',
    description: 'Introduction and status quo',
    color: 'bg-blue-500/10 border-blue-500/30',
  },
  {
    value: 'inciting_incident',
    label: 'Inciting Incident',
    description: 'Event that launches the plot',
    color: 'bg-amber-500/10 border-amber-500/30',
  },
  {
    value: 'rising_action',
    label: 'Rising Action',
    description: 'Building tension and complications',
    color: 'bg-purple-500/10 border-purple-500/30',
  },
  {
    value: 'climax',
    label: 'Climax',
    description: 'Peak of dramatic tension',
    color: 'bg-red-500/10 border-red-500/30',
  },
  {
    value: 'resolution',
    label: 'Resolution',
    description: 'Aftermath and new status quo',
    color: 'bg-green-500/10 border-green-500/30',
  },
];

interface ChapterBoardProps {
  storyId: string;
  chapterId: string;
}

/**
 * View mode for the chapter.
 */
type ViewMode = 'board' | 'list';

/**
 * Draggable scene card component.
 */
interface SceneCardProps {
  scene: SceneResponse;
  isDragging?: boolean;
}

function SceneCard({ scene, isDragging }: SceneCardProps) {
  const {
    setNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({
    id: scene.id,
    data: {
      type: 'scene',
      scene,
    },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group relative rounded-lg border bg-background p-3 shadow-sm transition-shadow hover:shadow-md',
        isDragging || isSortableDragging ? 'opacity-50 shadow-lg' : ''
      )}
    >
      <div className="flex items-start gap-2">
        <button
          className="mt-1 cursor-grab text-muted-foreground hover:text-foreground"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <div className="min-w-0 flex-1">
          <h4 className="truncate text-sm font-medium">{scene.title}</h4>
          {scene.summary && (
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
              {scene.summary}
            </p>
          )}
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {scene.beat_count} {scene.beat_count === 1 ? 'beat' : 'beats'}
            </Badge>
            {scene.location && (
              <span className="truncate text-xs text-muted-foreground">
                📍 {scene.location}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Kanban column component for a story phase.
 */
interface PhaseColumnProps {
  phase: (typeof STORY_PHASES)[0];
  scenes: SceneResponse[];
  onSceneClick?: (scene: SceneResponse) => void;
}

function PhaseColumn({ phase, scenes, onSceneClick }: PhaseColumnProps) {
  const sceneIds = scenes.map((s) => s.id);

  return (
    <div
      className={cn(
        'flex min-w-[280px] max-w-[320px] flex-col rounded-lg border p-4',
        phase.color
      )}
    >
      <div className="mb-4">
        <h3 className="text-sm font-semibold">{phase.label}</h3>
        <p className="mt-1 text-xs text-muted-foreground">{phase.description}</p>
        <Badge variant="secondary" className="mt-2">
          {scenes.length} {scenes.length === 1 ? 'scene' : 'scenes'}
        </Badge>
      </div>

      <SortableContext items={sceneIds} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-3">
          {scenes.map((scene) => (
            <div
              key={scene.id}
              onClick={() => onSceneClick?.(scene)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSceneClick?.(scene);
                }
              }}
              className="cursor-pointer"
              role="button"
              tabIndex={0}
            >
              <SceneCard scene={scene} />
            </div>
          ))}
          {scenes.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Drop scenes here
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

/**
 * List view component as alternative to board view.
 */
interface ListViewProps {
  scenes: SceneResponse[];
  onSceneClick?: (scene: SceneResponse) => void;
}

function ListView({ scenes, onSceneClick }: ListViewProps) {
  return (
    <div className="space-y-2">
      {scenes.map((scene) => (
        <Card
          key={scene.id}
          className="cursor-pointer transition-colors hover:bg-accent/50"
          onClick={() => onSceneClick?.(scene)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onSceneClick?.(scene);
            }
          }}
          role="button"
          tabIndex={0}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h4 className="font-medium">{scene.title}</h4>
                {scene.summary && (
                  <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
                    {scene.summary}
                  </p>
                )}
              </div>
              <Badge variant="outline" className="ml-4">
                {scene.beat_count} {scene.beat_count === 1 ? 'beat' : 'beats'}
              </Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * Main ChapterBoard component.
 */
export function ChapterBoard({ storyId, chapterId }: ChapterBoardProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('board');
  const [activeId, setActiveId] = useState<string | null>(null);

  const { data: scenesData, isLoading } = useScenes(storyId, chapterId);
  const updateScenePhase = useUpdateScenePhase();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Only start drag after moving 8px
      },
    })
  );

  // Group scenes by story phase for board view
  const scenesByPhase = useMemo(() => {
    const scenes = scenesData?.scenes ?? [];
    const grouped: Record<StoryPhase, SceneResponse[]> = {
      setup: [],
      inciting_incident: [],
      rising_action: [],
      climax: [],
      resolution: [],
    };

    scenes.forEach((scene) => {
      grouped[scene.story_phase].push(scene);
    });

    return grouped;
  }, [scenesData]);

  const activeScene = useMemo(() => {
    if (!activeId || !scenesData) return null;
    return scenesData.scenes.find((s) => s.id === activeId) ?? null;
  }, [activeId, scenesData]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || !scenesData) return;

    const activeScene = scenesData.scenes.find((s) => s.id === active.id);
    if (!activeScene) return;

    // Find which phase column was dropped on
    const overData = over.data.current as { type?: string; scene?: SceneResponse };
    if (overData?.type === 'scene') {
      // Get the phase of the target scene (the scene we dropped onto)
      const targetScene = overData.scene;
      if (targetScene && targetScene.story_phase !== activeScene.story_phase) {
        // Update the scene's phase
        updateScenePhase.mutate({
          storyId,
          chapterId,
          sceneId: activeScene.id,
          storyPhase: targetScene.story_phase,
        });
      }
    }
  };

  const handleSceneClick = (scene: SceneResponse) => {
    // Could open scene detail modal or navigate to scene editor
    console.log('Scene clicked:', scene);
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-muted-foreground">Loading scenes...</div>
      </div>
    );
  }

  const allScenes = scenesData?.scenes ?? [];

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Chapter Board</h2>
          <Badge variant="secondary">{allScenes.length} scenes</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Select value={viewMode} onValueChange={(v) => setViewMode(v as ViewMode)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="View mode" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="board">
                <div className="flex items-center gap-2">
                  <LayoutGrid className="h-4 w-4" />
                  Board
                </div>
              </SelectItem>
              <SelectItem value="list">
                <div className="flex items-center gap-2">
                  <LayoutList className="h-4 w-4" />
                  List
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        {viewMode === 'board' ? (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <div className="flex gap-4 pb-4">
              {STORY_PHASES.map((phase) => (
                <PhaseColumn
                  key={phase.value}
                  phase={phase}
                  scenes={scenesByPhase[phase.value]}
                  onSceneClick={handleSceneClick}
                />
              ))}
            </div>
            <DragOverlay>
              {activeScene ? <SceneCard scene={activeScene} isDragging /> : null}
            </DragOverlay>
          </DndContext>
        ) : (
          <div className="mx-auto max-w-3xl pb-4">
            <ListView scenes={allScenes} onSceneClick={handleSceneClick} />
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
