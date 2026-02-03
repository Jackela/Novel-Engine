/**
 * ForeshadowingPanel - Manage narrative setups and payoffs (DIR-053)
 *
 * Provides a comprehensive interface for tracking Chekhov's Gun elements:
 * - List all foreshadowing items with status filters
 * - Create new foreshadowing setups
 * - Link payoff scenes to setups
 * - Visual status indicators (PLANTED/PAID_OFF/ABANDONED)
 * - Group by status for quick overview
 */
import { useState, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import {
  useForeshadowings,
  useCreateForeshadowing,
  useUpdateForeshadowing,
  useLinkPayoff,
  useDeleteForeshadowing,
  foreshadowingKeys,
} from '../api/foreshadowingApi';
import type { ForeshadowingResponse, ForeshadowingStatus } from '@/types/schemas';
import {
  ChevronRight,
  Plus,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Link2,
  Trash2,
  Edit,
  Save,
  X,
} from 'lucide-react';

// Status configuration
const STATUS_CONFIG = {
  planted: {
    label: 'Planted',
    icon: AlertCircle,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500',
  },
  paid_off: {
    label: 'Paid Off',
    icon: CheckCircle2,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500',
  },
  abandoned: {
    label: 'Abandoned',
    icon: XCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500',
  },
} as const;

type StatusFilter = ForeshadowingStatus | 'all';

/**
 * Single foreshadowing item component with inline editing
 */
function ForeshadowingItem({
  foreshadowing,
  sceneOptions, // Available scenes for linking payoff
  onUpdate,
  onLinkPayoff,
  onDelete,
}: {
  foreshadowing: ForeshadowingResponse;
  sceneOptions: Array<{ id: string; title: string }>;
  onUpdate: (id: string, description: string, status: ForeshadowingStatus) => void;
  onLinkPayoff: (id: string, payoffSceneId: string) => void;
  onDelete: (id: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLinking, setIsLinking] = useState(false);
  const [editDescription, setEditDescription] = useState(foreshadowing.description);
  const [editStatus, setEditStatus] = useState<ForeshadowingStatus>(foreshadowing.status);
  const [selectedPayoffScene, setSelectedPayoffScene] = useState<string>(
    foreshadowing.payoff_scene_id || ''
  );

  const status = foreshadowing.status as keyof typeof STATUS_CONFIG;
  const config = STATUS_CONFIG[status];
  const StatusIcon = config.icon;

  const handleSave = () => {
    onUpdate(foreshadowing.id, editDescription, editStatus);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditDescription(foreshadowing.description);
    setEditStatus(foreshadowing.status);
    setIsEditing(false);
  };

  const handleLinkPayoff = () => {
    if (selectedPayoffScene) {
      onLinkPayoff(foreshadowing.id, selectedPayoffScene);
      setIsLinking(false);
    }
  };

  return (
    <div className="group border-b border-border/50 py-3 last:border-0">
      <div className="flex items-start gap-3">
        {/* Status indicator */}
        <div className={cn('mt-0.5', config.color)}>
          <StatusIcon className="h-4 w-4" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="space-y-2">
              <Textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="min-h-[60px] text-sm"
                placeholder="Describe the setup..."
              />
              <Select value={editStatus} onValueChange={(v) => setEditStatus(v as ForeshadowingStatus)}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(STATUS_CONFIG).map(([key, { label }]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={handleSave}>
                  <Save className="h-3 w-3 mr-1" />
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={handleCancel}>
                  <X className="h-3 w-3 mr-1" />
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm leading-relaxed">{foreshadowing.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="outline" className={cn('text-xs', config.borderColor, config.color)}>
                  {config.label}
                </Badge>
                {foreshadowing.payoff_scene_id && (
                  <Badge variant="outline" className="text-xs">
                    Payoff linked
                  </Badge>
                )}
              </div>
            </>
          )}
        </div>

        {/* Actions */}
        {!isEditing && (
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              onClick={() => setIsEditing(true)}
              title="Edit"
            >
              <Edit className="h-3 w-3" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              onClick={() => setIsLinking(true)}
              title="Link payoff scene"
              disabled={foreshadowing.status === 'abandoned'}
            >
              <Link2 className="h-3 w-3" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-destructive"
              onClick={() => setIsDeleting(true)}
              title="Delete"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      {/* Link Payoff Dialog */}
      <Dialog open={isLinking} onOpenChange={setIsLinking}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link Payoff Scene</DialogTitle>
            <DialogDescription>
              Select the scene where this foreshadowing is paid off.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Select value={selectedPayoffScene} onValueChange={setSelectedPayoffScene}>
              <SelectTrigger>
                <SelectValue placeholder="Select a scene" />
              </SelectTrigger>
              <SelectContent>
                {sceneOptions.map((scene) => (
                  <SelectItem key={scene.id} value={scene.id}>
                    {scene.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLinking(false)}>
              Cancel
            </Button>
            <Button onClick={handleLinkPayoff} disabled={!selectedPayoffScene}>
              Link
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleting} onOpenChange={setIsDeleting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Foreshadowing?</DialogTitle>
            <DialogDescription>
              This will remove this foreshadowing setup permanently. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleting(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => onDelete(foreshadowing.id)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Create foreshadowing dialog
 */
function CreateForeshadowingDialog({
  open,
  onOpenChange,
  setupSceneTitle,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  setupSceneTitle: string;
  onCreate: (description: string) => void;
}) {
  const [description, setDescription] = useState('');

  const handleCreate = () => {
    if (description.trim()) {
      onCreate(description.trim());
      setDescription('');
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Foreshadowing Setup</DialogTitle>
          <DialogDescription>
            Plant a narrative gun in "{setupSceneTitle}" that will be paid off later.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what you're planting... (e.g., 'The mysterious locket', 'The recurring nightmare')"
              className="min-h-[80px]"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={!description.trim()}>
            Plant Setup
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Main panel component
 */
export function ForeshadowingPanel({
  setupSceneId,
  setupSceneTitle,
  allScenes,
}: {
  setupSceneId?: string;
  setupSceneTitle?: string;
  allScenes?: Array<{ id: string; title: string }>;
}) {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Query foreshadowings
  const { data: foreshadowingsData, isLoading } = useForeshadowings();
  const foreshadowings = foreshadowingsData?.foreshadowings || [];

  // Mutations
  const createMutation = useCreateForeshadowing();
  const updateMutation = useUpdateForeshadowing();
  const linkPayoffMutation = useLinkPayoff();
  const deleteMutation = useDeleteForeshadowing();

  // Filter foreshadowings by status
  const filteredForeshadowings = useMemo(() => {
    if (statusFilter === 'all') {
      return foreshadowings;
    }
    return foreshadowings.filter((f) => f.status === statusFilter);
  }, [foreshadowings, statusFilter]);

  // Group by status for display
  const groupedForeshadowings = useMemo(() => {
    const groups: Partial<Record<ForeshadowingStatus, ForeshadowingResponse[]>> = {
      planted: [],
      paid_off: [],
      abandoned: [],
    };

    filteredForeshadowings.forEach((f) => {
      const status = f.status as ForeshadowingStatus;
      if (!groups[status]) {
        groups[status] = [];
      }
      groups[status]!.push(f);
    });

    return groups;
  }, [filteredForeshadowings]);

  // Count by status
  const statusCounts = useMemo(() => {
    return {
      planted: foreshadowings.filter((f) => f.status === 'planted').length,
      paid_off: foreshadowings.filter((f) => f.status === 'paid_off').length,
      abandoned: foreshadowings.filter((f) => f.status === 'abandoned').length,
      all: foreshadowings.length,
    };
  }, [foreshadowings]);

  // Handlers
  const handleCreate = async (description: string) => {
    if (!setupSceneId) {
      return;
    }

    try {
      await createMutation.mutateAsync({
        setup_scene_id: setupSceneId,
        description,
        status: 'planted',
      });
      queryClient.invalidateQueries({ queryKey: foreshadowingKeys.lists() });
    } catch (error) {
      console.error('Failed to create foreshadowing:', error);
    }
  };

  const handleUpdate = async (id: string, description: string, status: ForeshadowingStatus) => {
    try {
      await updateMutation.mutateAsync({
        id,
        request: { description, status },
      });
      queryClient.invalidateQueries({ queryKey: foreshadowingKeys.lists() });
    } catch (error) {
      console.error('Failed to update foreshadowing:', error);
    }
  };

  const handleLinkPayoff = async (id: string, payoffSceneId: string) => {
    try {
      await linkPayoffMutation.mutateAsync({
        id,
        request: { payoff_scene_id: payoffSceneId },
      });
      queryClient.invalidateQueries({ queryKey: foreshadowingKeys.lists() });
    } catch (error) {
      console.error('Failed to link payoff:', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
      queryClient.invalidateQueries({ queryKey: foreshadowingKeys.lists() });
    } catch (error) {
      console.error('Failed to delete foreshadowing:', error);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-500" />
          <h3 className="font-semibold">Foreshadowing</h3>
          <Badge variant="outline">{statusCounts.all}</Badge>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setCreateDialogOpen(true)}
          disabled={!setupSceneId}
        >
          <Plus className="h-4 w-4 mr-1" />
          Plant
        </Button>
      </div>

      {/* Status Filters */}
      <div className="flex gap-2 flex-wrap">
        <Button
          size="sm"
          variant={statusFilter === 'all' ? 'default' : 'outline'}
          onClick={() => setStatusFilter('all')}
          className="text-xs"
        >
          All ({statusCounts.all})
        </Button>
        <Button
          size="sm"
          variant={statusFilter === 'planted' ? 'default' : 'outline'}
          onClick={() => setStatusFilter('planted')}
          className="text-xs"
        >
          Planted ({statusCounts.planted})
        </Button>
        <Button
          size="sm"
          variant={statusFilter === 'paid_off' ? 'default' : 'outline'}
          onClick={() => setStatusFilter('paid_off')}
          className="text-xs"
        >
          Paid Off ({statusCounts.paid_off})
        </Button>
        <Button
          size="sm"
          variant={statusFilter === 'abandoned' ? 'default' : 'outline'}
          onClick={() => setStatusFilter('abandoned')}
          className="text-xs"
        >
          Abandoned ({statusCounts.abandoned})
        </Button>
      </div>

      {/* Foreshadowing List */}
      <ScrollArea className="h-[400px]">
        {isLoading ? (
          <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
            Loading foreshadowings...
          </div>
        ) : filteredForeshadowings.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            {statusFilter === 'all'
              ? 'No foreshadowings yet. Plant your first setup!'
              : `No ${statusFilter} foreshadowings.`}
          </div>
        ) : (
          <div className="space-y-1">
            {Object.entries(groupedForeshadowings).map(([status, items]) =>
              items && items.length > 0 ? (
                <Collapsible key={status} defaultOpen>
                  <CollapsibleTrigger className="flex items-center gap-2 w-full py-2 hover:bg-accent rounded px-2 transition-colors">
                    <ChevronRight className="h-4 w-4 transition-transform ui-expanded:rotate-90" />
                    <span className="font-medium text-sm capitalize">
                      {status.replace('_', ' ')}
                    </span>
                    <Badge variant="outline" className="text-xs ml-auto">
                      {items.length}
                    </Badge>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="pt-1">
                    {items.map((item) => (
                      <ForeshadowingItem
                        key={item.id}
                        foreshadowing={item}
                        sceneOptions={allScenes || []}
                        onUpdate={handleUpdate}
                        onLinkPayoff={handleLinkPayoff}
                        onDelete={handleDelete}
                      />
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              ) : null
            )}
          </div>
        )}
      </ScrollArea>

      {/* Create Dialog */}
      {setupSceneId && setupSceneTitle && (
        <CreateForeshadowingDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
          setupSceneTitle={setupSceneTitle}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}
