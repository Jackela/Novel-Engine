/**
 * PromptEditorPage - Prompt Lab editor with syntax highlighting
 *
 * BRAIN-019B: Prompt Lab - Editor
 * Provides full editing capabilities for prompt templates with:
 * - Content editor with {{variable}} syntax highlighting
 * - Variable definition table
 * - Model configuration selector
 * - Version history sidebar
 * - Autosave to localStorage
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams } from '@tanstack/react-router';
import { usePrompt, usePromptVersions, useUpdatePrompt, useCreatePrompt } from '../api/promptApi';
import {
  Card,
  CardDescription,
  CardHeader,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ErrorState } from '@/shared/components/feedback';
import { EmptyState } from '@/shared/components/feedback';
import {
  Save,
  ArrowLeft,
  Plus,
  Trash2,
  History,
  Settings,
  FileText,
  Variable as VariableIcon,
  AlertCircle,
  Loader2,
  Tag,
} from 'lucide-react';
import type {
  PromptVariableDefinition,
  PromptVariableType,
  PromptSummary,
} from '@/types/schemas';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

// Local storage key for autosave
const AUTOSAVE_KEY_PREFIX = 'prompt_autosave_';

// Variable type options matching PromptVariableTypeEnum
const VARIABLE_TYPES: { value: PromptVariableType; label: string }[] = [
  { value: 'string', label: 'Text' },
  { value: 'integer', label: 'Integer' },
  { value: 'float', label: 'Number' },
  { value: 'boolean', label: 'True/False' },
  { value: 'list', label: 'List' },
  { value: 'dict', label: 'Dictionary' },
];

// Provider options
const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'ollama', label: 'Ollama (Local)' },
];

// Model suggestions per provider
const MODEL_SUGGESTIONS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
  gemini: ['gemini-pro', 'gemini-ultra'],
  ollama: ['llama3', 'mistral', 'phi3'],
};

interface PromptFormData {
  name: string;
  description: string;
  content: string;
  tags: string[];
  extends: string[];
  variables: PromptVariableDefinition[];
  model_provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
}

const INITIAL_FORM_DATA: PromptFormData = {
  name: '',
  description: '',
  content: '',
  tags: [],
  extends: [],
  variables: [],
  model_provider: 'openai',
  model_name: 'gpt-4o',
  temperature: 0.7,
  max_tokens: 1000,
  top_p: 1.0,
  frequency_penalty: 0.0,
  presence_penalty: 0.0,
};

export function PromptEditorPage() {
  const params = useParams({ strict: false });
  const id = params.id as string;
  const isNew = id === 'new';
  const navigate = useNavigate();

  // Queries
  const { data: promptData, isLoading, error } = usePrompt(id || '');
  const { data: versionsData } = usePromptVersions(id || '');

  // Mutations
  const updateMutation = useUpdatePrompt();
  const createMutation = useCreatePrompt();

  // Form state
  const [formData, setFormData] = useState<PromptFormData>(INITIAL_FORM_DATA);
  const [tagInput, setTagInput] = useState('');
  const [extendsInput, setExtendsInput] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'content' | 'variables' | 'config' | 'history'>('content');

  // Load prompt data into form
  useEffect(() => {
    if (promptData && !isNew) {
      setFormData({
        name: promptData.name,
        description: promptData.description,
        content: promptData.content,
        tags: promptData.tags,
        extends: promptData.extends || [],
        variables: promptData.variables || [],
        model_provider: promptData.model_provider || 'openai',
        model_name: promptData.model_name || 'gpt-4o',
        temperature: promptData.temperature ?? 0.7,
        max_tokens: promptData.max_tokens ?? 1000,
        top_p: promptData.top_p ?? 1.0,
        frequency_penalty: promptData.frequency_penalty ?? 0.0,
        presence_penalty: promptData.presence_penalty ?? 0.0,
      });
    }
  }, [promptData, isNew]);

  // Autosave to localStorage
  useEffect(() => {
    if (!hasUnsavedChanges) return;

    const autosaveKey = AUTOSAVE_KEY_PREFIX + (isNew ? 'new' : id);
    const timer = setTimeout(() => {
      localStorage.setItem(autosaveKey, JSON.stringify(formData));
    }, 1000);

    return () => clearTimeout(timer);
  }, [formData, hasUnsavedChanges, isNew, id]);

  // Load autosaved data on mount for new prompts
  useEffect(() => {
    if (isNew) {
      const autosaveKey = AUTOSAVE_KEY_PREFIX + 'new';
      const saved = localStorage.getItem(autosaveKey);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setFormData(parsed);
          setHasUnsavedChanges(true);
        } catch {
          // Ignore invalid saved data
        }
      }
    }
  }, [isNew]);

  // Extract variables from content using regex
  const extractVariablesFromContent = useCallback((content: string): string[] => {
    const regex = /\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g;
    const variables = new Set<string>();
    let match;
    while ((match = regex.exec(content)) !== null) {
      if (match[1]) {
        variables.add(match[1]);
      }
    }
    return Array.from(variables);
  }, []);

  // Get variables that are in content but not in form
  const detectedVariables = extractVariablesFromContent(formData.content);
  const undefinedVariables = detectedVariables.filter(
    (v) => !formData.variables.some((fv) => fv.name === v)
  );

  // Update form field
  const updateField = <K extends keyof PromptFormData>(
    field: K,
    value: PromptFormData[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  // Add tag
  const addTag = () => {
    const trimmed = tagInput.trim().toLowerCase().replace(/[^a-z0-9-]/g, '');
    if (trimmed && !formData.tags.includes(trimmed)) {
      updateField('tags', [...formData.tags, trimmed]);
    }
    setTagInput('');
  };

  // Remove tag
  const removeTag = (tag: string) => {
    updateField('tags', formData.tags.filter((t) => t !== tag));
  };

  // Add extends reference
  const addExtends = () => {
    const trimmed = extendsInput.trim();
    if (trimmed && !formData.extends.includes(trimmed)) {
      updateField('extends', [...formData.extends, trimmed]);
    }
    setExtendsInput('');
  };

  // Remove extends reference
  const removeExtends = (ref: string) => {
    updateField('extends', formData.extends.filter((e) => e !== ref));
  };

  // Add variable
  const addVariable = () => {
    const newVar: PromptVariableDefinition = {
      name: '',
      type: 'string',
      default_value: null,
      description: '',
      required: true,
    };
    updateField('variables', [...formData.variables, newVar]);
  };

  // Update variable
  const updateVariable = (index: number, updates: Partial<PromptVariableDefinition>) => {
    const newVariables = [...formData.variables];
    // Ensure required fields have defaults
    const currentVar = newVariables[index];
    if (!currentVar) return;

    const mergedVar: PromptVariableDefinition = {
      name: updates.name ?? currentVar.name ?? '',
      type: updates.type ?? currentVar.type ?? 'string',
      description: updates.description ?? currentVar.description ?? '',
      required: updates.required ?? currentVar.required ?? true,
      default_value: updates.default_value !== undefined ? updates.default_value : currentVar.default_value,
    };
    newVariables[index] = mergedVar;
    updateField('variables', newVariables);
  };

  // Remove variable
  const removeVariable = (index: number) => {
    updateField('variables', formData.variables.filter((_, i) => i !== index));
  };

  // Add detected variables to form
  const addDetectedVariables = () => {
    const newVariables: PromptVariableDefinition[] = undefinedVariables.map((name) => ({
      name,
      type: 'string',
      default_value: null,
      description: '',
      required: true,
    }));

    // Merge with existing variables
    const mergedVariables = [...formData.variables];
    for (const newVar of newVariables) {
      if (!mergedVariables.some((v) => v.name === newVar.name)) {
        mergedVariables.push(newVar);
      }
    }

    updateField('variables', mergedVariables);
  };

  // Save prompt
  const savePrompt = async () => {
    if (!formData.name.trim()) {
      toast.error('Prompt name is required');
      return;
    }
    if (!formData.content.trim()) {
      toast.error('Prompt content is required');
      return;
    }

    setIsSaving(true);
    try {
      if (isNew) {
        const result = await createMutation.mutateAsync({
          name: formData.name,
          content: formData.content,
          description: formData.description,
          tags: formData.tags,
          extends: formData.extends,
          variables: formData.variables,
          model_provider: formData.model_provider || undefined,
          model_name: formData.model_name || undefined,
          temperature: formData.temperature,
          max_tokens: formData.max_tokens,
          top_p: formData.top_p,
          frequency_penalty: formData.frequency_penalty,
          presence_penalty: formData.presence_penalty,
        });

        // Clear autosave
        localStorage.removeItem(AUTOSAVE_KEY_PREFIX + 'new');

        toast.success('Prompt created successfully');
        navigate({ to: `/brain/prompts/${result.id}` });
      } else {
        await updateMutation.mutateAsync({
          id: id || '',
          name: formData.name,
          content: formData.content,
          description: formData.description,
          tags: formData.tags,
          extends: formData.extends,
          variables: formData.variables,
          model_provider: formData.model_provider || undefined,
          model_name: formData.model_name || undefined,
          temperature: formData.temperature,
          max_tokens: formData.max_tokens,
          top_p: formData.top_p,
          frequency_penalty: formData.frequency_penalty,
          presence_penalty: formData.presence_penalty,
        });

        // Clear autosave
        localStorage.removeItem(AUTOSAVE_KEY_PREFIX + id);

        setHasUnsavedChanges(false);
        toast.success('Prompt saved successfully (new version created)');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save prompt');
    } finally {
      setIsSaving(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error && !isNew) {
    return (
      <ErrorState
        title="Failed to load prompt"
        message={error.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate({ to: '/brain/prompts' })}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">
              {isNew ? 'New Prompt' : formData.name || 'Untitled Prompt'}
            </h1>
            {hasUnsavedChanges && (
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                Unsaved changes
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isNew && (
            <Button
              variant="outline"
              onClick={() => {
                localStorage.removeItem(AUTOSAVE_KEY_PREFIX + 'new');
                setFormData(INITIAL_FORM_DATA);
                setHasUnsavedChanges(false);
              }}
            >
              Clear Draft
            </Button>
          )}
          <Button
            onClick={savePrompt}
            disabled={isSaving || !hasUnsavedChanges}
          >
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save {isNew ? 'Prompt' : 'Changes'}
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Editor area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'content' | 'variables' | 'config' | 'history')} className="flex flex-col h-full">
            <div className="px-6 pt-4 border-b">
              <TabsList className="grid w-auto grid-cols-4">
                <TabsTrigger value="content">
                  <FileText className="mr-2 h-4 w-4" />
                  Content
                </TabsTrigger>
                <TabsTrigger value="variables">
                  <VariableIcon className="mr-2 h-4 w-4" />
                  Variables
                  {formData.variables.length > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {formData.variables.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="config">
                  <Settings className="mr-2 h-4 w-4" />
                  Config
                </TabsTrigger>
                <TabsTrigger value="history" disabled={isNew}>
                  <History className="mr-2 h-4 w-4" />
                  History
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Content Tab */}
            <TabsContent value="content" className="flex-1 overflow-hidden p-6 m-0">
              <div className="h-full flex flex-col gap-4">
                {/* Name input */}
                <div className="space-y-2">
                  <Label htmlFor="prompt-name">Prompt Name</Label>
                  <Input
                    id="prompt-name"
                    placeholder="e.g., Character Dialogue Generator"
                    value={formData.name}
                    onChange={(e) => updateField('name', e.target.value)}
                  />
                </div>

                {/* Description input */}
                <div className="space-y-2">
                  <Label htmlFor="prompt-description">Description</Label>
                  <Input
                    id="prompt-description"
                    placeholder="What does this prompt do?"
                    value={formData.description}
                    onChange={(e) => updateField('description', e.target.value)}
                  />
                </div>

                {/* Tags */}
                <div className="space-y-2">
                  <Label>Tags</Label>
                  <div className="flex flex-wrap gap-2 items-center">
                    {formData.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="gap-1">
                        <Tag className="h-3 w-3" />
                        {tag}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4 p-0 hover:bg-transparent"
                          onClick={() => removeTag(tag)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </Badge>
                    ))}
                    <div className="flex gap-1">
                      <Input
                        placeholder="Add tag..."
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                        className="h-8 w-32"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8"
                        onClick={addTag}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Extends (inheritance) */}
                <div className="space-y-2">
                  <Label>Inherits From (Optional)</Label>
                  <div className="flex flex-wrap gap-2 items-center">
                    {formData.extends.length === 0 ? (
                      <span className="text-sm text-muted-foreground">No base templates</span>
                    ) : (
                      formData.extends.map((ext) => (
                        <Badge key={ext} variant="outline" className="gap-1">
                          {ext}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-4 w-4 p-0 hover:bg-transparent"
                            onClick={() => removeExtends(ext)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </Badge>
                      ))
                    )}
                    <div className="flex gap-1">
                      <Input
                        placeholder="Template ID or name..."
                        value={extendsInput}
                        onChange={(e) => setExtendsInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addExtends())}
                        className="h-8 w-48"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8"
                        onClick={addExtends}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Content editor with syntax highlighting */}
                <div className="flex-1 flex flex-col min-h-0">
                  <div className="flex items-center justify-between mb-2">
                    <Label>Prompt Content</Label>
                    {undefinedVariables.length > 0 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={addDetectedVariables}
                        className="text-xs"
                      >
                        <Plus className="mr-1 h-3 w-3" />
                        Add {undefinedVariables.length} detected variable{undefinedVariables.length > 1 ? 's' : ''}
                      </Button>
                    )}
                  </div>
                  <HighlightedTextarea
                    value={formData.content}
                    onChange={(e) => updateField('content', e.target.value)}
                    placeholder="Write your prompt here. Use {{variable_name}} for variables."
                    className="flex-1 font-mono text-sm resize-none"
                  />
                </div>
              </div>
            </TabsContent>

            {/* Variables Tab */}
            <TabsContent value="variables" className="flex-1 overflow-hidden p-6 m-0">
              <div className="h-full flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Variables</h3>
                    <p className="text-sm text-muted-foreground">
                      Define the variables used in your prompt template
                    </p>
                  </div>
                  <Button onClick={addVariable} size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Variable
                  </Button>
                </div>

                {formData.variables.length === 0 ? (
                  <EmptyState
                    title="No variables defined"
                    description="Add variables to make your prompt reusable"
                  />
                ) : (
                  <Card className="flex-1 overflow-hidden">
                    <ScrollArea className="h-full">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[150px]">Name</TableHead>
                            <TableHead className="w-[120px]">Type</TableHead>
                            <TableHead>Default Value</TableHead>
                            <TableHead className="w-[80px]">Required</TableHead>
                            <TableHead>Description</TableHead>
                            <TableHead className="w-[60px]"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {formData.variables.map((variable, index) => (
                            <VariableRow
                              key={index}
                              variable={variable}
                              detectedVariables={detectedVariables}
                              onChange={(updates) => updateVariable(index, updates)}
                              onRemove={() => removeVariable(index)}
                            />
                          ))}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  </Card>
                )}
              </div>
            </TabsContent>

            {/* Config Tab */}
            <TabsContent value="config" className="flex-1 overflow-auto p-6 m-0">
              <div className="max-w-2xl space-y-6">
                <div>
                  <h3 className="text-lg font-semibold">Model Configuration</h3>
                  <p className="text-sm text-muted-foreground">
                    Configure the LLM settings for this prompt
                  </p>
                </div>

                {/* Provider */}
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <Select
                    value={formData.model_provider}
                    onValueChange={(value) => {
                      updateField('model_provider', value);
                      // Update model name to first suggestion for provider
                      const suggestions = MODEL_SUGGESTIONS[value];
                      if (suggestions && suggestions.length > 0) {
                        updateField('model_name', suggestions[0] ?? 'gpt-4o');
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PROVIDER_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Model Name */}
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Select
                    value={formData.model_name}
                    onValueChange={(value) => updateField('model_name', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(MODEL_SUGGESTIONS[formData.model_provider] || []).map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                {/* Temperature */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Temperature</Label>
                    <span className="text-sm text-muted-foreground">{formData.temperature.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[formData.temperature]}
                    onValueChange={([value]) => updateField('temperature', value ?? 0.7)}
                    min={0}
                    max={2}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Lower = more focused, Higher = more creative
                  </p>
                </div>

                {/* Max Tokens */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Max Tokens</Label>
                    <span className="text-sm text-muted-foreground">{formData.max_tokens}</span>
                  </div>
                  <Slider
                    value={[formData.max_tokens]}
                    onValueChange={([value]) => updateField('max_tokens', value ?? 1000)}
                    min={100}
                    max={8000}
                    step={100}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Maximum length of the generated response
                  </p>
                </div>

                {/* Top P */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Top P</Label>
                    <span className="text-sm text-muted-foreground">{formData.top_p.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[formData.top_p]}
                    onValueChange={([value]) => updateField('top_p', value ?? 1.0)}
                    min={0}
                    max={1}
                    step={0.05}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Nucleus sampling threshold
                  </p>
                </div>

                {/* Frequency Penalty */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Frequency Penalty</Label>
                    <span className="text-sm text-muted-foreground">{formData.frequency_penalty.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[formData.frequency_penalty]}
                    onValueChange={([value]) => updateField('frequency_penalty', value ?? 0.0)}
                    min={-2}
                    max={2}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Reduce repetition of token frequencies
                  </p>
                </div>

                {/* Presence Penalty */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Presence Penalty</Label>
                    <span className="text-sm text-muted-foreground">{formData.presence_penalty.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[formData.presence_penalty]}
                    onValueChange={([value]) => updateField('presence_penalty', value ?? 0.0)}
                    min={-2}
                    max={2}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Reduce repetition of token presence
                  </p>
                </div>
              </div>
            </TabsContent>

            {/* History Tab */}
            <TabsContent value="history" className="flex-1 overflow-hidden p-6 m-0">
              <div className="h-full flex flex-col gap-4">
                <div>
                  <h3 className="text-lg font-semibold">Version History</h3>
                  <p className="text-sm text-muted-foreground">
                    Track changes to this prompt over time
                  </p>
                </div>

                {!versionsData || versionsData.prompts.length === 0 ? (
                  <EmptyState
                    title="No history yet"
                    description="Save your prompt to start tracking versions"
                  />
                ) : (
                  <ScrollArea className="flex-1">
                    <div className="space-y-3 pr-4">
                      {versionsData?.prompts.map((version, index, arr) => (
                        <VersionCard
                          key={version.id}
                          version={version}
                          isCurrent={index === 0}
                          totalCount={arr.length}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

interface VariableRowProps {
  variable: PromptVariableDefinition;
  detectedVariables: string[];
  onChange: (updates: Partial<PromptVariableDefinition>) => void;
  onRemove: () => void;
}

function VariableRow({ variable, detectedVariables, onChange, onRemove }: VariableRowProps) {
  const isDetected = detectedVariables.includes(variable.name);
  const isUndefined = variable.name === '';

  return (
    <TableRow className={isUndefined ? 'bg-destructive/10' : undefined}>
      <TableCell>
        <Input
          value={variable.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="variable_name"
          className={isDetected ? 'border-green-500' : ''}
        />
        {isDetected && (
          <p className="text-xs text-green-600 mt-1">Found in content</p>
        )}
      </TableCell>
      <TableCell>
        <Select
          value={variable.type}
          onValueChange={(value) => onChange({ type: value as PromptVariableType })}
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {VARIABLE_TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>
        <Input
          value={variable.default_value?.toString() || ''}
          onChange={(e) => onChange({ default_value: e.target.value || null })}
          placeholder="Default value"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Switch
            checked={variable.required}
            onCheckedChange={(checked) => onChange({ required: checked })}
          />
          <span className="text-xs text-muted-foreground">
            {variable.required ? 'Required' : 'Optional'}
          </span>
        </div>
      </TableCell>
      <TableCell>
        <Input
          value={variable.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder="Variable description"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <Button
          variant="ghost"
          size="icon"
          onClick={onRemove}
          className="h-8 w-8 text-destructive hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
}

interface VersionCardProps {
  version: PromptSummary;
  isCurrent: boolean;
  totalCount: number;
}

function VersionCard({ version, isCurrent }: VersionCardProps) {
  return (
    <Card className={isCurrent ? 'border-primary' : ''}>
      <CardHeader className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant={isCurrent ? 'default' : 'secondary'}>
              v{version.version}
            </Badge>
            {isCurrent && (
              <Badge variant="outline" className="text-xs">
                Current
              </Badge>
            )}
            <span className="text-sm font-medium">{version.name}</span>
          </div>
          <span className="text-xs text-muted-foreground">
            {new Date(version.updated_at).toLocaleString()}
          </span>
        </div>
        {version.description && (
          <CardDescription className="text-sm mt-1">
            {version.description}
          </CardDescription>
        )}
      </CardHeader>
    </Card>
  );
}

// Textarea with {{variable}} syntax highlighting
interface HighlightedTextareaProps extends React.ComponentProps<'textarea'> {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

function HighlightedTextarea({ value, onChange, className, ...props }: HighlightedTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e);
    // Sync scroll
    if (overlayRef.current && textareaRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
      overlayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  const handleScroll = () => {
    if (overlayRef.current && textareaRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
      overlayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  // Highlight variables in the text
  const getHighlightedHTML = (text: string) => {
    // Escape HTML
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Highlight {{variable}} patterns
    return escaped.replace(
      /\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g,
      '<mark class="bg-primary/20 text-primary rounded px-0.5 font-semibold">{{$1}}</mark>'
    );
  };

  return (
    <div className="relative w-full h-full">
      {/* Highlighting overlay */}
      <div
        ref={overlayRef}
        className="absolute inset-0 p-3 pointer-events-none whitespace-pre-wrap break-words font-mono text-sm overflow-hidden"
        style={{
          color: 'transparent',
        }}
        dangerouslySetInnerHTML={{ __html: getHighlightedHTML(value) }}
      />
      {/* Actual textarea */}
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onScroll={handleScroll}
        className={cn(
          'absolute inset-0 bg-transparent/80 resize-none',
          className
        )}
        {...props}
      />
    </div>
  );
}
