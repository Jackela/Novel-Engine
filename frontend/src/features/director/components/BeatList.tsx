/**
 * BeatList - A micro-editor for managing beats within a scene.
 *
 * Why: Beats are atomic narrative units that break scenes into ACTION/REACTION
 * micro-units. This component enables drag-and-drop reordering, inline editing,
 * and CRUD operations for Director Mode pacing analysis.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
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
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  GripVertical,
  Plus,
  Trash2,
  Check,
  X,
  Loader2,
  MessageSquare,
  Zap,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

import {
  useBeats,
  useCreateBeat,
  useUpdateBeat,
  useDeleteBeat,
  useReorderBeats,
} from '../api/beatApi';
import { BeatSuggestionPopover } from './BeatSuggestionPopover';
import type { BeatResponse, BeatType } from '@/types/schemas';

/**
 * Beat type configuration for visual styling and labels.
 */
const BEAT_TYPE_CONFIG: Record<
  BeatType,
  { label: string; borderColor: string; icon: typeof Zap }
> = {
  action: { label: 'Action', borderColor: 'border-blue-500', icon: Zap },
  dialogue: { label: 'Dialogue', borderColor: 'border-emerald-500', icon: MessageSquare },
  reaction: { label: 'Reaction', borderColor: 'border-amber-500', icon: Zap },
  revelation: { label: 'Revelation', borderColor: 'border-purple-500', icon: Zap },
  transition: { label: 'Transition', borderColor: 'border-gray-500', icon: Zap },
  description: { label: 'Description', borderColor: 'border-cyan-500', icon: Zap },
};

/**
 * Mood shift display helper.
 */
function getMoodShiftDisplay(value: number): { label: string; className: string } {
  if (value > 0) return { label: `+${value}`, className: 'text-green-500' };
  if (value < 0) return { label: `${value}`, className: 'text-red-500' };
  return { label: '0', className: 'text-muted-foreground' };
}

interface BeatItemProps {
  beat: BeatResponse;
  isEditing: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: (updates: { content?: string; beat_type?: BeatType; mood_shift?: number }) => void;
  onDelete: () => void;
  isSaving: boolean;
}

/**
 * SortableBeatItem - Individual beat card with drag handle and inline editing.
 */
function SortableBeatItem({
  beat,
  isEditing,
  onEdit,
  onCancelEdit,
  onSave,
  onDelete,
  isSaving,
}: BeatItemProps) {
  const [editContent, setEditContent] = useState(beat.content);
  const [editType, setEditType] = useState<BeatType>(beat.beat_type);
  const [editMoodShift, setEditMoodShift] = useState(beat.mood_shift);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: beat.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // Reset edit state when beat changes
  useEffect(() => {
    setEditContent(beat.content);
    setEditType(beat.beat_type);
    setEditMoodShift(beat.mood_shift);
  }, [beat.content, beat.beat_type, beat.mood_shift]);

  // Focus textarea when entering edit mode
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = useCallback(() => {
    const updates: { content?: string; beat_type?: BeatType; mood_shift?: number } = {};
    if (editContent !== beat.content) {
      updates.content = editContent;
    }
    if (editType !== beat.beat_type) {
      updates.beat_type = editType;
    }
    if (editMoodShift !== beat.mood_shift) {
      updates.mood_shift = editMoodShift;
    }
    onSave(updates);
  }, [editContent, editType, editMoodShift, beat, onSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancelEdit();
      } else if (e.key === 'Enter' && e.ctrlKey) {
        handleSave();
      }
    },
    [onCancelEdit, handleSave]
  );

  const typeConfig = BEAT_TYPE_CONFIG[beat.beat_type];
  const moodDisplay = getMoodShiftDisplay(beat.mood_shift);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group relative rounded-lg border-l-4 bg-card p-3 shadow-sm transition-all',
        typeConfig.borderColor,
        isDragging && 'opacity-50 shadow-lg',
        !isEditing && 'hover:bg-accent/50 cursor-pointer'
      )}
      onClick={!isEditing ? onEdit : undefined}
      onKeyDown={!isEditing ? (e) => e.key === 'Enter' && onEdit() : undefined}
      role={!isEditing ? 'button' : undefined}
      tabIndex={!isEditing ? 0 : undefined}
    >
      {/* Drag Handle */}
      <div
        {...attributes}
        {...listeners}
        className="absolute left-0 top-0 flex h-full w-6 cursor-grab items-center justify-center text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-4 w-4" />
      </div>

      <div className="ml-4">
        {/* Header: Type Badge + Mood Shift */}
        <div className="mb-2 flex items-center justify-between">
          {isEditing ? (
            <Select value={editType} onValueChange={(v) => setEditType(v as BeatType)}>
              <SelectTrigger className="h-7 w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(BEAT_TYPE_CONFIG) as BeatType[]).map((type) => (
                  <SelectItem key={type} value={type}>
                    {BEAT_TYPE_CONFIG[type].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Badge
              variant="outline"
              className={cn('text-xs', typeConfig.borderColor.replace('border-', 'text-'))}
            >
              {typeConfig.label}
            </Badge>
          )}

          <div className="flex items-center gap-2">
            {isEditing ? (
              <Select
                value={String(editMoodShift)}
                onValueChange={(v) => setEditMoodShift(Number(v))}
              >
                <SelectTrigger className="h-7 w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5].map((val) => (
                    <SelectItem key={val} value={String(val)}>
                      {val > 0 ? `+${val}` : val}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <span className={cn('text-xs font-medium', moodDisplay.className)}>
                Mood: {moodDisplay.label}
              </span>
            )}

            {/* Delete button - visible on hover or when editing */}
            {!isEditing && (
              <Dialog>
                <DialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Delete Beat</DialogTitle>
                    <DialogDescription>
                      Are you sure you want to delete this beat? This action cannot be
                      undone.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button variant="outline">Cancel</Button>
                    <Button variant="destructive" onClick={onDelete}>Delete</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
          </div>
        </div>

        {/* Content */}
        {isEditing ? (
          <div className="space-y-2">
            <Textarea
              ref={textareaRef}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter beat content..."
              className="min-h-20 resize-none"
              rows={3}
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={onCancelEdit} disabled={isSaving}>
                <X className="mr-1 h-3.5 w-3.5" />
                Cancel
              </Button>
              <Button size="sm" onClick={handleSave} disabled={isSaving}>
                {isSaving ? (
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Check className="mr-1 h-3.5 w-3.5" />
                )}
                Save
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Press Ctrl+Enter to save, Escape to cancel
            </p>
          </div>
        ) : (
          <p className="text-sm text-foreground/90">
            {beat.content || <span className="italic text-muted-foreground">Empty beat</span>}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Beat overlay shown during drag operations.
 */
function BeatDragOverlay({ beat }: { beat: BeatResponse }) {
  const typeConfig = BEAT_TYPE_CONFIG[beat.beat_type];

  return (
    <div
      className={cn(
        'rounded-lg border-l-4 bg-card p-3 shadow-lg',
        typeConfig.borderColor
      )}
    >
      <div className="ml-4">
        <Badge
          variant="outline"
          className={cn('mb-2 text-xs', typeConfig.borderColor.replace('border-', 'text-'))}
        >
          {typeConfig.label}
        </Badge>
        <p className="line-clamp-2 text-sm">
          {beat.content || <span className="italic text-muted-foreground">Empty beat</span>}
        </p>
      </div>
    </div>
  );
}

interface BeatListProps {
  /** Scene ID to load beats for */
  sceneId: string;
  /** Scene context for AI suggestions (setting, characters, situation) */
  sceneContext?: string;
  /** Optional CSS class name */
  className?: string;
}

/**
 * BeatList - Main component for managing scene beats.
 *
 * Features:
 * - Drag-and-drop reordering via dnd-kit
 * - Visual distinction: ACTION = blue border, REACTION = amber border
 * - Inline editing with save/cancel
 * - Add/Delete beat functionality
 * - API integration with optimistic updates
 */
export function BeatList({ sceneId, sceneContext = '', className }: BeatListProps) {
  const [editingBeatId, setEditingBeatId] = useState<string | null>(null);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const [isAddingBeat, setIsAddingBeat] = useState(false);
  const [newBeatType, setNewBeatType] = useState<BeatType>('action');
  const [newBeatContent, setNewBeatContent] = useState('');

  // API hooks
  const { data: beatData, isLoading, error } = useBeats(sceneId);
  const createBeat = useCreateBeat();
  const updateBeat = useUpdateBeat();
  const deleteBeat = useDeleteBeat();
  const reorderBeats = useReorderBeats();

  // dnd-kit sensors
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

  const beats = beatData?.beats ?? [];
  const activeDragBeat = activeDragId ? beats.find((b) => b.id === activeDragId) : null;

  // Drag handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveDragId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveDragId(null);

      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = beats.findIndex((b) => b.id === active.id);
      const newIndex = beats.findIndex((b) => b.id === over.id);

      if (oldIndex === -1 || newIndex === -1) return;

      // Compute new order
      const newOrder = [...beats];
      const movedItems = newOrder.splice(oldIndex, 1);
      const movedBeat = movedItems[0];
      if (!movedBeat) return;
      newOrder.splice(newIndex, 0, movedBeat);

      // Call API to persist reorder
      reorderBeats.mutate({
        sceneId,
        beatIds: newOrder.map((b) => b.id),
      });
    },
    [beats, reorderBeats, sceneId]
  );

  // Beat CRUD handlers
  const handleAddBeat = useCallback(() => {
    createBeat.mutate(
      {
        sceneId,
        input: {
          content: newBeatContent,
          beat_type: newBeatType,
          mood_shift: 0,
        },
      },
      {
        onSuccess: () => {
          setIsAddingBeat(false);
          setNewBeatContent('');
          setNewBeatType('action');
        },
      }
    );
  }, [createBeat, sceneId, newBeatContent, newBeatType]);

  const handleUpdateBeat = useCallback(
    (beatId: string, updates: { content?: string; beat_type?: BeatType; mood_shift?: number }) => {
      // Only send non-undefined updates
      const filteredUpdates = Object.fromEntries(
        Object.entries(updates).filter(([, v]) => v !== undefined)
      );

      if (Object.keys(filteredUpdates).length === 0) {
        setEditingBeatId(null);
        return;
      }

      updateBeat.mutate(
        {
          sceneId,
          beatId,
          updates: filteredUpdates,
        },
        {
          onSuccess: () => {
            setEditingBeatId(null);
          },
        }
      );
    },
    [updateBeat, sceneId]
  );

  const handleDeleteBeat = useCallback(
    (beatId: string) => {
      deleteBeat.mutate({ sceneId, beatId });
    },
    [deleteBeat, sceneId]
  );

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('p-4 text-center text-destructive', className)}>
        Failed to load beats. Please try again.
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header with Add and Spark buttons */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-muted-foreground">
          Scene Beats ({beats.length})
        </h3>
        <div className="flex items-center gap-2">
          {/* AI Spark Button - Writer's Block Breaker */}
          <BeatSuggestionPopover
            sceneId={sceneId}
            currentBeats={beats}
            sceneContext={sceneContext}
            onSelectSuggestion={(suggestion) => {
              // Auto-create the beat from suggestion
              createBeat.mutate(
                {
                  sceneId,
                  input: {
                    content: suggestion.content,
                    beat_type: suggestion.beat_type,
                    mood_shift: suggestion.mood_shift,
                  },
                },
                {
                  onSuccess: () => {
                    // Optional: Show success feedback
                  },
                }
              );
            }}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAddingBeat(true)}
            disabled={isAddingBeat}
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            Add Beat
          </Button>
        </div>
      </div>

      {/* New Beat Form */}
      {isAddingBeat && (
        <div className="rounded-lg border border-dashed border-primary/50 bg-primary/5 p-3">
          <div className="mb-2 flex items-center gap-2">
            <Select value={newBeatType} onValueChange={(v) => setNewBeatType(v as BeatType)}>
              <SelectTrigger className="h-8 w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(BEAT_TYPE_CONFIG) as BeatType[]).map((type) => (
                  <SelectItem key={type} value={type}>
                    {BEAT_TYPE_CONFIG[type].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Textarea
            value={newBeatContent}
            onChange={(e) => setNewBeatContent(e.target.value)}
            placeholder="Enter beat content..."
            className="mb-2 min-h-16 resize-none"
            rows={2}
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsAddingBeat(false);
                setNewBeatContent('');
              }}
              disabled={createBeat.isPending}
            >
              Cancel
            </Button>
            <Button size="sm" onClick={handleAddBeat} disabled={createBeat.isPending}>
              {createBeat.isPending ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="mr-1 h-3.5 w-3.5" />
              )}
              Add Beat
            </Button>
          </div>
        </div>
      )}

      {/* Beat List with DnD */}
      <ScrollArea className="h-96">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={beats.map((b) => b.id)} strategy={verticalListSortingStrategy}>
            <div className="space-y-2 pr-4">
              {beats.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  No beats yet. Add your first beat to start building the scene.
                </div>
              ) : (
                beats.map((beat) => (
                  <SortableBeatItem
                    key={beat.id}
                    beat={beat}
                    isEditing={editingBeatId === beat.id}
                    onEdit={() => setEditingBeatId(beat.id)}
                    onCancelEdit={() => setEditingBeatId(null)}
                    onSave={(updates) => handleUpdateBeat(beat.id, updates)}
                    onDelete={() => handleDeleteBeat(beat.id)}
                    isSaving={updateBeat.isPending}
                  />
                ))
              )}
            </div>
          </SortableContext>

          {/* Drag Overlay */}
          <DragOverlay>
            {activeDragBeat ? <BeatDragOverlay beat={activeDragBeat} /> : null}
          </DragOverlay>
        </DndContext>
      </ScrollArea>
    </div>
  );
}

export default BeatList;
