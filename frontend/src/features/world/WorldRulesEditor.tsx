/**
 * WorldRulesEditor - Interface for managing world rules (magic systems, physics constraints).
 *
 * Provides CRUD operations for WorldRule entities using a card-based layout.
 * Each rule displays name, description, consequence, and exceptions (tag list).
 */
import { useState, useCallback, useEffect, type KeyboardEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Save, X, AlertTriangle, Shield, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type {
  WorldRuleResponse,
  WorldRuleCreateRequest,
  WorldRuleUpdateRequest,
} from '@/types/schemas';

const API_PREFIX = '/api';

// === API Functions ===

async function fetchWorldRules(): Promise<WorldRuleResponse[]> {
  const response = await fetch(`${API_PREFIX}/world-rules`);
  if (!response.ok) throw new Error('Failed to fetch world rules');
  const data = await response.json();
  return data.rules ?? [];
}

async function createWorldRule(
  rule: WorldRuleCreateRequest
): Promise<WorldRuleResponse> {
  const response = await fetch(`${API_PREFIX}/world-rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });
  if (!response.ok) throw new Error('Failed to create world rule');
  return response.json();
}

async function updateWorldRule(
  id: string,
  updates: WorldRuleUpdateRequest
): Promise<WorldRuleResponse> {
  const response = await fetch(`${API_PREFIX}/world-rules/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update world rule');
  return response.json();
}

async function deleteWorldRule(id: string): Promise<void> {
  const response = await fetch(`${API_PREFIX}/world-rules/${id}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204)
    throw new Error('Failed to delete world rule');
}

// === Helper Functions ===

function getSeverityInfo(severity: number): { label: string; color: string } {
  if (severity >= 90) return { label: 'Absolute', color: 'text-red-500' };
  if (severity >= 70) return { label: 'Strict', color: 'text-orange-500' };
  if (severity >= 40) return { label: 'Moderate', color: 'text-yellow-500' };
  return { label: 'Flexible', color: 'text-green-500' };
}

// === Sub-Components ===

interface ExceptionsEditorProps {
  exceptions: string[];
  onChange: (exceptions: string[]) => void;
}

function ExceptionsEditor({ exceptions, onChange }: ExceptionsEditorProps) {
  const [inputValue, setInputValue] = useState('');

  const addException = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed && !exceptions.includes(trimmed)) {
      onChange([...exceptions, trimmed]);
    }
    setInputValue('');
  }, [inputValue, exceptions, onChange]);

  const removeException = useCallback(
    (index: number) => onChange(exceptions.filter((_, i) => i !== index)),
    [exceptions, onChange]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addException();
      } else if (e.key === 'Backspace' && !inputValue && exceptions.length > 0) {
        removeException(exceptions.length - 1);
      }
    },
    [addException, removeException, inputValue, exceptions.length]
  );

  return (
    <div className="space-y-2">
      <Label>Exceptions</Label>
      {exceptions.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {exceptions.map((exception, idx) => (
            <Badge key={idx} variant="secondary" className="gap-1 pr-1">
              {exception}
              <button
                type="button"
                onClick={() => removeException(idx)}
                className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20"
                aria-label={`Remove ${exception}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      <Input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type an exception and press Enter"
      />
    </div>
  );
}

interface RuleFormFieldsProps {
  name: string;
  setName: (v: string) => void;
  category: string;
  setCategory: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
  consequence: string;
  setConsequence: (v: string) => void;
  severity: number;
  setSeverity: (v: number) => void;
  exceptions: string[];
  setExceptions: (v: string[]) => void;
  idPrefix: string;
}

function RuleFormFields({
  name,
  setName,
  category,
  setCategory,
  description,
  setDescription,
  consequence,
  setConsequence,
  severity,
  setSeverity,
  exceptions,
  setExceptions,
  idPrefix,
}: RuleFormFieldsProps) {
  return (
    <>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-name`}>
          Name <span className="text-destructive">*</span>
        </Label>
        <Input
          id={`${idPrefix}-name`}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Rule name"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-category`}>Category</Label>
        <Input
          id={`${idPrefix}-category`}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          placeholder="e.g., magic, physics, social"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-description`}>Description</Label>
        <Textarea
          id={`${idPrefix}-description`}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What does this rule govern?"
          rows={2}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-consequence`}>Consequence</Label>
        <Textarea
          id={`${idPrefix}-consequence`}
          value={consequence}
          onChange={(e) => setConsequence(e.target.value)}
          placeholder="What happens when violated?"
          rows={2}
        />
      </div>
      <div className="space-y-2">
        <Label>Severity: {severity}</Label>
        <Slider
          value={[severity]}
          onValueChange={([val]) => setSeverity(val ?? 50)}
          min={0}
          max={100}
          step={5}
        />
        <p className="text-xs text-muted-foreground">
          {getSeverityInfo(severity).label} - How strictly enforced
        </p>
      </div>
      <ExceptionsEditor exceptions={exceptions} onChange={setExceptions} />
    </>
  );
}

interface RuleDisplayCardProps {
  rule: WorldRuleResponse;
  onEdit: () => void;
  onDelete: () => void;
  isDeleting: boolean;
}

function RuleDisplayCard({ rule, onEdit, onDelete, isDeleting }: RuleDisplayCardProps) {
  const severityInfo = getSeverityInfo(rule.severity);

  return (
    <Card data-testid={`rule-card-${rule.id}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">{rule.name}</CardTitle>
            {rule.category && (
              <Badge variant="outline" className="text-xs">
                {rule.category}
              </Badge>
            )}
          </div>
          <div className={`text-xs font-medium ${severityInfo.color}`}>
            {severityInfo.label} ({rule.severity})
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {rule.description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">
            {rule.description}
          </p>
        )}
        {rule.consequence && (
          <div>
            <p className="text-xs font-medium text-muted-foreground">Consequence:</p>
            <p className="line-clamp-2 text-sm">{rule.consequence}</p>
          </div>
        )}
        {rule.exceptions.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium text-muted-foreground">
              Exceptions:
            </p>
            <div className="flex flex-wrap gap-1">
              {rule.exceptions.slice(0, 3).map((exc, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs">
                  {exc}
                </Badge>
              ))}
              {rule.exceptions.length > 3 && (
                <Badge variant="secondary" className="text-xs">
                  +{rule.exceptions.length - 3} more
                </Badge>
              )}
            </div>
          </div>
        )}
      </CardContent>
      <CardFooter className="gap-2 pt-0">
        <Button variant="outline" size="sm" className="flex-1" onClick={onEdit}>
          Edit
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onDelete}
          disabled={isDeleting}
          className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
        >
          {isDeleting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}

interface RuleEditCardProps {
  rule: WorldRuleResponse;
  onSave: (updates: WorldRuleUpdateRequest) => void;
  onCancel: () => void;
  isSaving: boolean;
}

function RuleEditCard({ rule, onSave, onCancel, isSaving }: RuleEditCardProps) {
  const [name, setName] = useState(rule.name);
  const [description, setDescription] = useState(rule.description);
  const [consequence, setConsequence] = useState(rule.consequence);
  const [exceptions, setExceptions] = useState<string[]>(rule.exceptions);
  const [category, setCategory] = useState(rule.category);
  const [severity, setSeverity] = useState(rule.severity);

  const handleSave = () => {
    if (!name.trim()) {
      toast.error('Name is required');
      return;
    }
    onSave({ name, description, consequence, exceptions, category, severity });
  };

  return (
    <Card className="border-primary" data-testid={`rule-edit-card-${rule.id}`}>
      <CardHeader className="pb-3">
        <CardDescription>Editing Rule</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <RuleFormFields
          name={name}
          setName={setName}
          category={category}
          setCategory={setCategory}
          description={description}
          setDescription={setDescription}
          consequence={consequence}
          setConsequence={setConsequence}
          severity={severity}
          setSeverity={setSeverity}
          exceptions={exceptions}
          setExceptions={setExceptions}
          idPrefix="edit"
        />
      </CardContent>
      <CardFooter className="gap-2 pt-0">
        <Button variant="outline" size="sm" onClick={onCancel} disabled={isSaving}>
          <X className="mr-1 h-4 w-4" />
          Cancel
        </Button>
        <Button size="sm" onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <Loader2 className="mr-1 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-1 h-4 w-4" />
          )}
          Save
        </Button>
      </CardFooter>
    </Card>
  );
}

interface CreateRuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: WorldRuleCreateRequest) => void;
  isSubmitting: boolean;
}

function CreateRuleDialog({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
}: CreateRuleDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [consequence, setConsequence] = useState('');
  const [exceptions, setExceptions] = useState<string[]>([]);
  const [category, setCategory] = useState('');
  const [severity, setSeverity] = useState(50);

  useEffect(() => {
    if (!open) {
      setName('');
      setDescription('');
      setConsequence('');
      setExceptions([]);
      setCategory('');
      setSeverity(50);
    }
  }, [open]);

  const handleSubmit = () => {
    if (!name.trim()) {
      toast.error('Name is required');
      return;
    }
    onSubmit({ name, description, consequence, exceptions, category, severity });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create World Rule</DialogTitle>
          <DialogDescription>
            Define a new law or magic system rule for your world.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <RuleFormFields
            name={name}
            setName={setName}
            category={category}
            setCategory={setCategory}
            description={description}
            setDescription={setDescription}
            consequence={consequence}
            setConsequence={setConsequence}
            severity={severity}
            setSeverity={setSeverity}
            exceptions={exceptions}
            setExceptions={setExceptions}
            idPrefix="create"
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Create Rule
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// === Empty State Component ===

interface EmptyRulesStateProps {
  onCreate: () => void;
}

function EmptyRulesState({ onCreate }: EmptyRulesStateProps) {
  return (
    <div className="rounded-lg border border-dashed p-8 text-center">
      <Shield className="mx-auto h-12 w-12 text-muted-foreground/50" />
      <h3 className="mt-4 text-lg font-medium">No world rules yet</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Create your first rule to define how your world works
      </p>
      <Button variant="outline" className="mt-4" onClick={onCreate}>
        <Plus className="mr-2 h-4 w-4" />
        Create First Rule
      </Button>
    </div>
  );
}

// === Rules Grid Component ===

interface RulesGridProps {
  rules: WorldRuleResponse[];
  editingRuleId: string | null;
  setEditingRuleId: (id: string | null) => void;
  onUpdate: (id: string, updates: WorldRuleUpdateRequest) => void;
  onDelete: (id: string) => void;
  isUpdating: boolean;
  isDeleting: boolean;
}

function RulesGrid({
  rules,
  editingRuleId,
  setEditingRuleId,
  onUpdate,
  onDelete,
  isUpdating,
  isDeleting,
}: RulesGridProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {rules.map((rule) =>
        editingRuleId === rule.id ? (
          <RuleEditCard
            key={rule.id}
            rule={rule}
            onSave={(updates) => onUpdate(rule.id, updates)}
            onCancel={() => setEditingRuleId(null)}
            isSaving={isUpdating}
          />
        ) : (
          <RuleDisplayCard
            key={rule.id}
            rule={rule}
            onEdit={() => setEditingRuleId(rule.id)}
            onDelete={() => onDelete(rule.id)}
            isDeleting={isDeleting}
          />
        )
      )}
    </div>
  );
}

// === Hooks ===

function useWorldRulesMutations(
  setIsCreateDialogOpen: (v: boolean) => void,
  setEditingRuleId: (v: string | null) => void
) {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: createWorldRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['world-rules'] });
      setIsCreateDialogOpen(false);
      toast.success('World rule created');
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Failed to create rule'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: WorldRuleUpdateRequest }) =>
      updateWorldRule(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['world-rules'] });
      setEditingRuleId(null);
      toast.success('World rule updated');
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Failed to update rule'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWorldRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['world-rules'] });
      toast.success('World rule deleted');
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Failed to delete rule'),
  });

  return { createMutation, updateMutation, deleteMutation };
}

// === Loading/Error States ===

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

function ErrorState() {
  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center">
      <AlertTriangle className="mx-auto h-8 w-8 text-destructive" />
      <p className="mt-2 text-sm text-destructive">Failed to load world rules</p>
    </div>
  );
}

// === Main Component ===

export function WorldRulesEditor() {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const {
    data: rules = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['world-rules'],
    queryFn: fetchWorldRules,
  });

  const { createMutation, updateMutation, deleteMutation } = useWorldRulesMutations(
    setIsCreateDialogOpen,
    setEditingRuleId
  );

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState />;

  return (
    <div className="space-y-6" data-testid="world-rules-editor">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">World Rules</h2>
          <p className="text-sm text-muted-foreground">
            Define the laws and constraints of your world
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Rule
        </Button>
      </div>

      {rules.length === 0 ? (
        <EmptyRulesState onCreate={() => setIsCreateDialogOpen(true)} />
      ) : (
        <RulesGrid
          rules={rules}
          editingRuleId={editingRuleId}
          setEditingRuleId={setEditingRuleId}
          onUpdate={(id, updates) => updateMutation.mutate({ id, updates })}
          onDelete={(id) => deleteMutation.mutate(id)}
          isUpdating={updateMutation.isPending}
          isDeleting={deleteMutation.isPending}
        />
      )}

      <CreateRuleDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        onSubmit={(data) => createMutation.mutate(data)}
        isSubmitting={createMutation.isPending}
      />
    </div>
  );
}

export default WorldRulesEditor;
