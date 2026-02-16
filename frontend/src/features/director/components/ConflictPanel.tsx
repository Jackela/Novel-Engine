/**
 * ConflictPanel - Manages dramatic conflicts within scenes.
 *
 * Why: No conflict, no story. This component enables tracking of dramatic
 * tensions with INTERNAL/EXTERNAL/INTERPERSONAL types, stakes levels, and
 * resolution status. Critical for Director Mode pacing analysis.
 */
import { useState, useCallback, useMemo } from 'react';
import {
  Flame,
  Plus,
  Trash2,
  ChevronDown,
  Loader2,
  AlertTriangle,
  Users,
  Brain,
  Swords,
  Check,
  X,
  TrendingUp,
  RotateCcw,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
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
  useConflicts,
  useCreateConflict,
  useUpdateConflict,
  useDeleteConflict,
} from '../api/conflictApi';
import type {
  ConflictResponse,
  ConflictType,
  ConflictStakes,
  ResolutionStatus,
} from '@/types/schemas';

/**
 * Conflict type configuration for visual styling, icons, and labels.
 */
const CONFLICT_TYPE_CONFIG: Record<
  ConflictType,
  { label: string; icon: typeof Brain; description: string }
> = {
  internal: {
    label: 'Internal',
    icon: Brain,
    description: 'Character vs. Self - inner struggles, moral dilemmas',
  },
  external: {
    label: 'External',
    icon: Swords,
    description: 'Character vs. World - nature, society, circumstances',
  },
  interpersonal: {
    label: 'Interpersonal',
    icon: Users,
    description: 'Character vs. Character - relationships, antagonists',
  },
};

/**
 * Stakes level configuration for visual styling.
 */
const STAKES_CONFIG: Record<
  ConflictStakes,
  {
    label: string;
    className: string;
    badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline';
  }
> = {
  low: {
    label: 'Low',
    className: 'text-muted-foreground',
    badgeVariant: 'outline',
  },
  medium: {
    label: 'Medium',
    className: 'text-yellow-500',
    badgeVariant: 'secondary',
  },
  high: {
    label: 'High',
    className: 'text-orange-500',
    badgeVariant: 'default',
  },
  critical: {
    label: 'Critical',
    className: 'text-red-500',
    badgeVariant: 'destructive',
  },
};

/**
 * Resolution status configuration.
 */
const RESOLUTION_CONFIG: Record<
  ResolutionStatus,
  { label: string; icon: typeof AlertTriangle; className: string }
> = {
  unresolved: {
    label: 'Unresolved',
    icon: AlertTriangle,
    className: 'text-yellow-500',
  },
  escalating: {
    label: 'Escalating',
    icon: TrendingUp,
    className: 'text-orange-500',
  },
  resolved: {
    label: 'Resolved',
    icon: Check,
    className: 'text-green-500',
  },
};

interface ConflictItemProps {
  conflict: ConflictResponse;
  isEditing: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: (updates: Partial<ConflictResponse>) => void;
  onDelete: () => void;
  onEscalate: () => void;
  onResolve: () => void;
  onReopen: () => void;
  isSaving: boolean;
}

/**
 * Individual conflict card with inline editing and status actions.
 */
function ConflictItem({
  conflict,
  isEditing,
  onEdit,
  onCancelEdit,
  onSave,
  onDelete,
  onEscalate,
  onResolve,
  onReopen,
  isSaving,
}: ConflictItemProps) {
  const [editDescription, setEditDescription] = useState(conflict.description);
  const [editType, setEditType] = useState<ConflictType>(conflict.conflict_type);
  const [editStakes, setEditStakes] = useState<ConflictStakes>(conflict.stakes);

  const stakesConfig = STAKES_CONFIG[conflict.stakes];
  const resolutionConfig = RESOLUTION_CONFIG[conflict.resolution_status];
  const typeConfig = CONFLICT_TYPE_CONFIG[conflict.conflict_type];
  const TypeIcon = typeConfig.icon;
  const ResolutionIcon = resolutionConfig.icon;
  const isCritical = conflict.stakes === 'critical';
  const isResolved = conflict.resolution_status === 'resolved';

  const handleSave = useCallback(() => {
    const updates: Partial<ConflictResponse> = {};
    if (editDescription !== conflict.description) {
      updates.description = editDescription;
    }
    if (editType !== conflict.conflict_type) {
      updates.conflict_type = editType;
    }
    if (editStakes !== conflict.stakes) {
      updates.stakes = editStakes;
    }
    onSave(updates);
  }, [editDescription, editType, editStakes, conflict, onSave]);

  return (
    <div
      className={cn(
        'group relative rounded-lg border bg-card p-3 transition-all',
        isCritical && !isResolved && 'border-red-500/50 bg-red-500/5',
        isResolved && 'opacity-60',
        !isEditing && 'cursor-pointer hover:bg-accent/50'
      )}
      onClick={!isEditing ? onEdit : undefined}
      onKeyDown={!isEditing ? (e) => e.key === 'Enter' && onEdit() : undefined}
      role={!isEditing ? 'button' : undefined}
      tabIndex={!isEditing ? 0 : undefined}
    >
      {/* Critical stakes indicator */}
      {isCritical && !isResolved && (
        <div className="absolute -right-1 -top-1">
          <Flame className="h-4 w-4 animate-pulse text-red-500" />
        </div>
      )}

      {/* Header: Type + Stakes + Resolution */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {isEditing ? (
            <Select
              value={editType}
              onValueChange={(v) => setEditType(v as ConflictType)}
            >
              <SelectTrigger className="h-7 w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(CONFLICT_TYPE_CONFIG) as ConflictType[]).map((type) => (
                  <SelectItem key={type} value={type}>
                    <span className="flex items-center gap-1">
                      {React.createElement(CONFLICT_TYPE_CONFIG[type].icon, {
                        className: 'h-3 w-3',
                      })}
                      {CONFLICT_TYPE_CONFIG[type].label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Badge variant="outline" className="flex items-center gap-1 text-xs">
              <TypeIcon className="h-3 w-3" />
              {typeConfig.label}
            </Badge>
          )}

          {isEditing ? (
            <Select
              value={editStakes}
              onValueChange={(v) => setEditStakes(v as ConflictStakes)}
            >
              <SelectTrigger className="h-7 w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(STAKES_CONFIG) as ConflictStakes[]).map((level) => (
                  <SelectItem key={level} value={level}>
                    {STAKES_CONFIG[level].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Badge variant={stakesConfig.badgeVariant} className="text-xs">
              {stakesConfig.label} Stakes
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Resolution status badge */}
          <Badge
            variant="outline"
            className={cn('text-xs', resolutionConfig.className)}
          >
            <ResolutionIcon className="mr-1 h-3 w-3" />
            {resolutionConfig.label}
          </Badge>

          {/* Delete button */}
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
                  <DialogTitle>Delete Conflict</DialogTitle>
                  <DialogDescription>
                    Are you sure you want to delete this conflict? This action cannot be
                    undone.
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
        <div className="space-y-2">
          <Textarea
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            placeholder="Describe the conflict..."
            className="min-h-16 resize-none"
            rows={2}
            autoFocus
          />
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {/* Status action buttons */}
              {conflict.resolution_status === 'unresolved' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEscalate();
                  }}
                  disabled={isSaving}
                  className="text-xs"
                >
                  <TrendingUp className="mr-1 h-3 w-3" />
                  Escalate
                </Button>
              )}
              {conflict.resolution_status !== 'resolved' && (
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
              )}
              {conflict.resolution_status === 'resolved' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onReopen();
                  }}
                  disabled={isSaving}
                  className="text-xs"
                >
                  <RotateCcw className="mr-1 h-3 w-3" />
                  Reopen
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
        <p className="text-sm text-foreground/90">
          {conflict.description || (
            <span className="italic text-muted-foreground">No description</span>
          )}
        </p>
      )}
    </div>
  );
}

// Need to import React for createElement
import * as React from 'react';

interface ConflictPanelProps {
  /** Scene ID to load conflicts for */
  sceneId: string;
  /** Optional CSS class name */
  className?: string;
}

/**
 * ConflictPanel - Panel for managing conflicts within a scene.
 *
 * Features:
 * - Collapsible sections by conflict type (INTERNAL/EXTERNAL/INTERPERSONAL)
 * - Visual cue: CRITICAL stakes show fire/red indicator
 * - Badge showing unresolved conflict count
 * - CRUD operations with inline editing
 * - Status transitions (escalate/resolve/reopen)
 */
export function ConflictPanel({ sceneId, className }: ConflictPanelProps) {
  const [editingConflictId, setEditingConflictId] = useState<string | null>(null);
  const [isAddingConflict, setIsAddingConflict] = useState(false);
  const [newConflictType, setNewConflictType] = useState<ConflictType>('external');
  const [newConflictStakes, setNewConflictStakes] = useState<ConflictStakes>('medium');
  const [newConflictDescription, setNewConflictDescription] = useState('');

  // Track which sections are open (all open by default)
  const [openSections, setOpenSections] = useState<Record<ConflictType, boolean>>({
    internal: true,
    external: true,
    interpersonal: true,
  });

  // API hooks
  const { data: conflictData, isLoading, error } = useConflicts(sceneId);
  const createConflict = useCreateConflict();
  const updateConflict = useUpdateConflict();
  const deleteConflict = useDeleteConflict();

  const conflicts = useMemo(
    () => conflictData?.conflicts ?? [],
    [conflictData?.conflicts]
  );

  // Group conflicts by type
  const conflictsByType = useMemo(() => {
    const grouped: Record<ConflictType, ConflictResponse[]> = {
      internal: [],
      external: [],
      interpersonal: [],
    };
    for (const conflict of conflicts) {
      grouped[conflict.conflict_type].push(conflict);
    }
    return grouped;
  }, [conflicts]);

  // Count unresolved conflicts
  const unresolvedCount = useMemo(
    () => conflicts.filter((c) => c.resolution_status !== 'resolved').length,
    [conflicts]
  );

  // Count critical unresolved conflicts
  const criticalCount = useMemo(
    () =>
      conflicts.filter(
        (c) => c.stakes === 'critical' && c.resolution_status !== 'resolved'
      ).length,
    [conflicts]
  );

  // Handlers
  const handleAddConflict = useCallback(() => {
    createConflict.mutate(
      {
        sceneId,
        input: {
          conflict_type: newConflictType,
          stakes: newConflictStakes,
          description: newConflictDescription,
          resolution_status: 'unresolved',
        },
      },
      {
        onSuccess: () => {
          setIsAddingConflict(false);
          setNewConflictDescription('');
          setNewConflictType('external');
          setNewConflictStakes('medium');
        },
      }
    );
  }, [
    createConflict,
    sceneId,
    newConflictType,
    newConflictStakes,
    newConflictDescription,
  ]);

  const handleUpdateConflict = useCallback(
    (conflictId: string, updates: Partial<ConflictResponse>) => {
      if (Object.keys(updates).length === 0) {
        setEditingConflictId(null);
        return;
      }

      updateConflict.mutate(
        {
          sceneId,
          conflictId,
          updates,
        },
        {
          onSuccess: () => {
            setEditingConflictId(null);
          },
        }
      );
    },
    [updateConflict, sceneId]
  );

  const handleDeleteConflict = useCallback(
    (conflictId: string) => {
      deleteConflict.mutate({ sceneId, conflictId });
    },
    [deleteConflict, sceneId]
  );

  const handleStatusChange = useCallback(
    (conflictId: string, newStatus: ResolutionStatus) => {
      updateConflict.mutate({
        sceneId,
        conflictId,
        updates: { resolution_status: newStatus },
      });
    },
    [updateConflict, sceneId]
  );

  const toggleSection = useCallback((type: ConflictType) => {
    setOpenSections((prev) => ({ ...prev, [type]: !prev[type] }));
  }, []);

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
        Failed to load conflicts. Please try again.
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header with Add button and unresolved count badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-muted-foreground">Conflicts</h3>
          {unresolvedCount > 0 && (
            <Badge
              variant={criticalCount > 0 ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {criticalCount > 0 && <Flame className="mr-1 h-3 w-3" />}
              {unresolvedCount} unresolved
            </Badge>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsAddingConflict(true)}
          disabled={isAddingConflict}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add Conflict
        </Button>
      </div>

      {/* New Conflict Form */}
      {isAddingConflict && (
        <div className="rounded-lg border border-dashed border-primary/50 bg-primary/5 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Select
              value={newConflictType}
              onValueChange={(v) => setNewConflictType(v as ConflictType)}
            >
              <SelectTrigger className="h-8 w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(CONFLICT_TYPE_CONFIG) as ConflictType[]).map((type) => (
                  <SelectItem key={type} value={type}>
                    <span className="flex items-center gap-1">
                      {React.createElement(CONFLICT_TYPE_CONFIG[type].icon, {
                        className: 'h-3 w-3',
                      })}
                      {CONFLICT_TYPE_CONFIG[type].label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={newConflictStakes}
              onValueChange={(v) => setNewConflictStakes(v as ConflictStakes)}
            >
              <SelectTrigger className="h-8 w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(STAKES_CONFIG) as ConflictStakes[]).map((level) => (
                  <SelectItem key={level} value={level}>
                    {STAKES_CONFIG[level].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Textarea
            value={newConflictDescription}
            onChange={(e) => setNewConflictDescription(e.target.value)}
            placeholder="Describe the conflict..."
            className="mb-2 min-h-16 resize-none"
            rows={2}
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsAddingConflict(false);
                setNewConflictDescription('');
              }}
              disabled={createConflict.isPending}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleAddConflict}
              disabled={createConflict.isPending}
            >
              {createConflict.isPending ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="mr-1 h-3.5 w-3.5" />
              )}
              Add Conflict
            </Button>
          </div>
        </div>
      )}

      {/* Collapsible sections by conflict type */}
      <ScrollArea className="h-80">
        <div className="space-y-2 pr-4">
          {(Object.keys(CONFLICT_TYPE_CONFIG) as ConflictType[]).map((type) => {
            const typeConflicts = conflictsByType[type];
            const config = CONFLICT_TYPE_CONFIG[type];
            const Icon = config.icon;
            const unresolvedInType = typeConflicts.filter(
              (c) => c.resolution_status !== 'resolved'
            ).length;

            return (
              <Collapsible
                key={type}
                open={openSections[type]}
                onOpenChange={() => toggleSection(type)}
              >
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    className="flex w-full items-center justify-between px-2 py-1.5 hover:bg-accent/50"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">{config.label}</span>
                      {typeConflicts.length > 0 && (
                        <Badge variant="outline" className="text-xs">
                          {typeConflicts.length}
                        </Badge>
                      )}
                      {unresolvedInType > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {unresolvedInType} active
                        </Badge>
                      )}
                    </div>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 text-muted-foreground transition-transform',
                        openSections[type] && 'rotate-180'
                      )}
                    />
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-2 pt-2">
                  {typeConflicts.length === 0 ? (
                    <p className="py-2 text-center text-xs text-muted-foreground">
                      No {config.label.toLowerCase()} conflicts
                    </p>
                  ) : (
                    typeConflicts.map((conflict) => (
                      <ConflictItem
                        key={conflict.id}
                        conflict={conflict}
                        isEditing={editingConflictId === conflict.id}
                        onEdit={() => setEditingConflictId(conflict.id)}
                        onCancelEdit={() => setEditingConflictId(null)}
                        onSave={(updates) => handleUpdateConflict(conflict.id, updates)}
                        onDelete={() => handleDeleteConflict(conflict.id)}
                        onEscalate={() => handleStatusChange(conflict.id, 'escalating')}
                        onResolve={() => handleStatusChange(conflict.id, 'resolved')}
                        onReopen={() => handleStatusChange(conflict.id, 'unresolved')}
                        isSaving={updateConflict.isPending}
                      />
                    ))
                  )}
                </CollapsibleContent>
              </Collapsible>
            );
          })}

          {conflicts.length === 0 && !isAddingConflict && (
            <div className="py-8 text-center text-muted-foreground">
              No conflicts yet. Add your first conflict to drive the story forward.
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

export default ConflictPanel;
