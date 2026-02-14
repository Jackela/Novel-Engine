/**
 * PlotlineManager - Manages narrative threads that weave through the story.
 *
 * Why: Stories often have multiple concurrent plotlines (main plot, subplots,
 * character arcs). This component enables tracking these threads with visual
 * color coding, status management, and scene counting for Director Mode.
 */
import { useState, useCallback, useMemo } from 'react';
import {
  Plus,
  Trash2,
  Loader2,
  Check,
  X,
  FolderOpen,
  Ban,
  RotateCcw,
  Hash,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { defaultPlotlineColor, plotlinePalette } from '@/styles/tokens';

import {
  usePlotlines,
  useCreatePlotline,
  useUpdatePlotline,
  useDeletePlotline,
} from '../api/plotlineApi';
import type { PlotlineResponse, PlotlineStatus } from '@/types/schemas';

/**
 * Predefined color palette for plotlines.
 * Why: Ensures visual consistency and accessibility. Colors are distinct
 * and work well in both light and dark themes.
 */
const PLOTLINE_COLORS = plotlinePalette;

/**
 * Plotline status configuration.
 */
const STATUS_CONFIG: Record<
  PlotlineStatus,
  {
    label: string;
    icon: typeof FolderOpen;
    className: string;
    badgeVariant: 'default' | 'secondary' | 'outline';
  }
> = {
  active: {
    label: 'Active',
    icon: FolderOpen,
    className: 'text-green-500',
    badgeVariant: 'default',
  },
  resolved: {
    label: 'Resolved',
    icon: Check,
    className: 'text-blue-500',
    badgeVariant: 'secondary',
  },
  abandoned: {
    label: 'Abandoned',
    icon: Ban,
    className: 'text-muted-foreground',
    badgeVariant: 'outline',
  },
};

interface PlotlineItemProps {
  plotline: PlotlineResponse;
  isEditing: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: (updates: Partial<PlotlineResponse>) => void;
  onDelete: () => void;
  onResolve: () => void;
  onAbandon: () => void;
  onReactivate: () => void;
  isSaving: boolean;
  sceneCount?: number;
}

/**
 * Individual plotline card with inline editing and status actions.
 */
function PlotlineItem({
  plotline,
  isEditing,
  onEdit,
  onCancelEdit,
  onSave,
  onDelete,
  onResolve,
  onAbandon,
  onReactivate,
  isSaving,
  sceneCount = 0,
}: PlotlineItemProps) {
  const [editName, setEditName] = useState(plotline.name);
  const [editDescription, setEditDescription] = useState(plotline.description);
  const [editColor, setEditColor] = useState(plotline.color);
  const [editStatus, setEditStatus] = useState<PlotlineStatus>(plotline.status);

  const statusConfig = STATUS_CONFIG[plotline.status];
  const StatusIcon = statusConfig.icon;
  const isActive = plotline.status === 'active';
  const isAbandoned = plotline.status === 'abandoned';

  const handleSave = useCallback(() => {
    const updates: Partial<PlotlineResponse> = {};
    if (editName !== plotline.name) {
      updates.name = editName;
    }
    if (editDescription !== plotline.description) {
      updates.description = editDescription;
    }
    if (editColor !== plotline.color) {
      updates.color = editColor;
    }
    if (editStatus !== plotline.status) {
      updates.status = editStatus;
    }
    onSave(updates);
  }, [editName, editDescription, editColor, editStatus, plotline, onSave]);

  return (
    <div
      className={cn(
        'group relative rounded-lg border bg-card p-4 transition-all',
        isAbandoned && 'opacity-50',
        !isEditing && 'cursor-pointer hover:bg-accent/50'
      )}
      onClick={!isEditing ? onEdit : undefined}
      onKeyDown={!isEditing ? (e) => e.key === 'Enter' && onEdit() : undefined}
      role={!isEditing ? 'button' : undefined}
      tabIndex={!isEditing ? 0 : undefined}
    >
      {/* Color indicator bar */}
      <div
        className="absolute bottom-4 left-0 top-4 w-1 rounded-r-full"
        style={{ backgroundColor: plotline.color }}
      />

      {/* Header: Name + Status + Actions */}
      <div className="mb-3 flex items-start justify-between gap-2 pl-3">
        <div className="flex-1 space-y-2">
          {isEditing ? (
            <div className="space-y-2">
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Plotline name..."
                className="h-8"
                autoFocus
              />
              <div className="flex gap-2">
                {/* Color picker */}
                <Select value={editColor} onValueChange={setEditColor}>
                  <SelectTrigger className="h-8 w-32">
                    <SelectValue placeholder="Color" />
                  </SelectTrigger>
                  <SelectContent>
                    {PLOTLINE_COLORS.map((color) => (
                      <SelectItem key={color.value} value={color.value}>
                        <span className="flex items-center gap-2">
                          <div
                            className={cn('h-3 w-3 rounded-full', color.className)}
                            style={{ backgroundColor: color.value }}
                          />
                          {color.label}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Status picker */}
                <Select
                  value={editStatus}
                  onValueChange={(v) => setEditStatus(v as PlotlineStatus)}
                >
                  <SelectTrigger className="h-8 w-32">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(STATUS_CONFIG) as PlotlineStatus[]).map((status) => (
                      <SelectItem key={status} value={status}>
                        {STATUS_CONFIG[status].label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold">{plotline.name}</h4>
              <Badge
                variant={statusConfig.badgeVariant}
                className={cn('text-xs', statusConfig.className)}
              >
                <StatusIcon className="mr-1 h-3 w-3" />
                {statusConfig.label}
              </Badge>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
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
                  <DialogTitle>Delete Plotline</DialogTitle>
                  <DialogDescription>
                    Are you sure you want to delete this plotline? This will remove it
                    from all scenes. This action cannot be undone.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline">Cancel</Button>
                  <Button variant="destructive" onClick={onDelete}>
                    Delete
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* Description */}
      {isEditing ? (
        <div className="space-y-3 pl-3">
          <Textarea
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            placeholder="Describe this plotline..."
            className="min-h-16 resize-none"
            rows={2}
          />
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {/* Status action buttons */}
              {isActive && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onResolve();
                    }}
                    disabled={isSaving}
                    className="text-xs"
                  >
                    <Check className="mr-1 h-3 w-3" />
                    Resolve
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onAbandon();
                    }}
                    disabled={isSaving}
                    className="text-xs"
                  >
                    <Ban className="mr-1 h-3 w-3" />
                    Abandon
                  </Button>
                </>
              )}
              {!isActive && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onReactivate();
                  }}
                  disabled={isSaving}
                  className="text-xs"
                >
                  <RotateCcw className="mr-1 h-3 w-3" />
                  Reactivate
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={onCancelEdit}
                disabled={isSaving}
              >
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
          </div>
        </div>
      ) : (
        <div className="pl-3">
          <p className="text-sm text-foreground/90">
            {plotline.description || (
              <span className="italic text-muted-foreground">No description</span>
            )}
          </p>
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <Hash className="h-3 w-3" />
            <span>
              {sceneCount} scene{sceneCount !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

interface PlotlineManagerProps {
  /** Optional scene ID to show plotline counts */
  sceneId?: string;
  /** Optional callback when plotline is selected */
  onSelectPlotline?: (plotlineId: string) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Main PlotlineManager component with sidebar layout.
 *
 * Why: Provides a centralized panel for managing all plotlines in the story.
 * Shows scene counts per plotline and enables quick CRUD operations.
 */
export function PlotlineManager({
  sceneId,
  onSelectPlotline,
  className,
}: PlotlineManagerProps) {
  const { data: plotlines, isLoading: isLoadingPlotlines } = usePlotlines();

  const createMutation = useCreatePlotline();
  const updateMutation = useUpdatePlotline();
  const deleteMutation = useDeletePlotline();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newPlotline, setNewPlotline] = useState({
    name: '',
    color: defaultPlotlineColor,
    description: '',
  });

  // Scene counts are now included in the API response (scene_count field)
  const sceneCounts = useMemo<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    plotlines?.plotlines.forEach((p) => {
      counts[p.id] = p.scene_count ?? 0;
    });
    return counts;
  }, [plotlines]);

  const handleCreatePlotline = useCallback(async () => {
    if (!newPlotline.name.trim()) return;

    try {
      await createMutation.mutateAsync({
        name: newPlotline.name.trim(),
        color: newPlotline.color,
        description: newPlotline.description.trim(),
        status: 'active',
      });
      setIsCreateDialogOpen(false);
      setNewPlotline({ name: '', color: defaultPlotlineColor, description: '' });
    } catch (error) {
      console.error('Failed to create plotline:', error);
    }
  }, [newPlotline, createMutation]);

  const handleUpdatePlotline = useCallback(
    async (plotlineId: string, updates: Partial<PlotlineResponse>) => {
      try {
        await updateMutation.mutateAsync({
          plotlineId,
          updates,
        });
        setEditingId(null);
      } catch (error) {
        console.error('Failed to update plotline:', error);
      }
    },
    [updateMutation]
  );

  const handleDeletePlotline = useCallback(
    async (plotlineId: string) => {
      try {
        await deleteMutation.mutateAsync(plotlineId);
        if (editingId === plotlineId) {
          setEditingId(null);
        }
      } catch (error) {
        console.error('Failed to delete plotline:', error);
      }
    },
    [deleteMutation, editingId]
  );

  const handleResolve = useCallback(
    async (plotlineId: string) => {
      await handleUpdatePlotline(plotlineId, { status: 'resolved' });
    },
    [handleUpdatePlotline]
  );

  const handleAbandon = useCallback(
    async (plotlineId: string) => {
      await handleUpdatePlotline(plotlineId, { status: 'abandoned' });
    },
    [handleUpdatePlotline]
  );

  const handleReactivate = useCallback(
    async (plotlineId: string) => {
      await handleUpdatePlotline(plotlineId, { status: 'active' });
    },
    [handleUpdatePlotline]
  );

  const groupedPlotlines = useMemo(() => {
    const active: PlotlineResponse[] = [];
    const resolved: PlotlineResponse[] = [];
    const abandoned: PlotlineResponse[] = [];

    plotlines?.plotlines.forEach((p) => {
      if (p.status === 'active') active.push(p);
      else if (p.status === 'resolved') resolved.push(p);
      else abandoned.push(p);
    });

    return { active, resolved, abandoned };
  }, [plotlines]);

  if (isLoadingPlotlines) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Plotlines</h3>
          <p className="text-xs text-muted-foreground">
            {plotlines?.plotlines.length ?? 0} thread
            {(plotlines?.plotlines.length ?? 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="gap-1">
              <Plus className="h-4 w-4" />
              New
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Plotline</DialogTitle>
              <DialogDescription>
                Add a new narrative thread to track through your story.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="plotline-name" className="text-sm font-medium">
                  Name
                </label>
                <Input
                  id="plotline-name"
                  value={newPlotline.name}
                  onChange={(e) =>
                    setNewPlotline({ ...newPlotline, name: e.target.value })
                  }
                  placeholder="e.g., Main Plot, Romance Arc, Mystery..."
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <span className="text-sm font-medium">Color</span>
                <div
                  className="flex flex-wrap gap-2"
                  role="group"
                  aria-label="Color selection"
                >
                  {PLOTLINE_COLORS.map((color) => (
                    <button
                      key={color.value}
                      type="button"
                      onClick={() =>
                        setNewPlotline({ ...newPlotline, color: color.value })
                      }
                      className={cn(
                        'h-8 w-8 rounded-full border-2 transition-all',
                        newPlotline.color === color.value
                          ? 'scale-110 border-foreground'
                          : 'border-transparent'
                      )}
                      style={{ backgroundColor: color.value }}
                      title={color.label}
                      aria-label={`Select ${color.label} color`}
                      aria-pressed={newPlotline.color === color.value}
                    />
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <label htmlFor="plotline-description" className="text-sm font-medium">
                  Description (optional)
                </label>
                <Textarea
                  id="plotline-description"
                  value={newPlotline.description}
                  onChange={(e) =>
                    setNewPlotline({ ...newPlotline, description: e.target.value })
                  }
                  placeholder="Briefly describe this narrative thread..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleCreatePlotline}
                disabled={!newPlotline.name.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Plotline list */}
      <ScrollArea className="flex-1">
        <div className="space-y-4 pr-4">
          {/* Active plotlines */}
          {groupedPlotlines.active.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                Active ({groupedPlotlines.active.length})
              </h4>
              {groupedPlotlines.active.map((plotline) => (
                <PlotlineItem
                  key={plotline.id}
                  plotline={plotline}
                  isEditing={editingId === plotline.id}
                  onEdit={() => setEditingId(plotline.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSave={(updates) => handleUpdatePlotline(plotline.id, updates)}
                  onDelete={() => handleDeletePlotline(plotline.id)}
                  onResolve={() => handleResolve(plotline.id)}
                  onAbandon={() => handleAbandon(plotline.id)}
                  onReactivate={() => handleReactivate(plotline.id)}
                  isSaving={updateMutation.isPending}
                  sceneCount={sceneCounts[plotline.id] ?? 0}
                />
              ))}
            </div>
          )}

          {/* Resolved plotlines */}
          {groupedPlotlines.resolved.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                Resolved ({groupedPlotlines.resolved.length})
              </h4>
              {groupedPlotlines.resolved.map((plotline) => (
                <PlotlineItem
                  key={plotline.id}
                  plotline={plotline}
                  isEditing={editingId === plotline.id}
                  onEdit={() => setEditingId(plotline.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSave={(updates) => handleUpdatePlotline(plotline.id, updates)}
                  onDelete={() => handleDeletePlotline(plotline.id)}
                  onResolve={() => handleResolve(plotline.id)}
                  onAbandon={() => handleAbandon(plotline.id)}
                  onReactivate={() => handleReactivate(plotline.id)}
                  isSaving={updateMutation.isPending}
                  sceneCount={sceneCounts[plotline.id] ?? 0}
                />
              ))}
            </div>
          )}

          {/* Abandoned plotlines */}
          {groupedPlotlines.abandoned.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                Abandoned ({groupedPlotlines.abandoned.length})
              </h4>
              {groupedPlotlines.abandoned.map((plotline) => (
                <PlotlineItem
                  key={plotline.id}
                  plotline={plotline}
                  isEditing={editingId === plotline.id}
                  onEdit={() => setEditingId(plotline.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSave={(updates) => handleUpdatePlotline(plotline.id, updates)}
                  onDelete={() => handleDeletePlotline(plotline.id)}
                  onResolve={() => handleResolve(plotline.id)}
                  onAbandon={() => handleAbandon(plotline.id)}
                  onReactivate={() => handleReactivate(plotline.id)}
                  isSaving={updateMutation.isPending}
                  sceneCount={sceneCounts[plotline.id] ?? 0}
                />
              ))}
            </div>
          )}

          {/* Empty state */}
          {plotlines?.plotlines.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Hash className="mb-2 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No plotlines yet</p>
              <p className="text-xs text-muted-foreground/70">
                Create a plotline to track narrative threads through your story
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
