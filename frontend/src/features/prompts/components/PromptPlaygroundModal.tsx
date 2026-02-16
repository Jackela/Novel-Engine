/**
 * PromptPlaygroundModal - Prompt playground for testing prompts
 *
 * BRAIN-020A: Frontend: Prompt Playground - UI
 * Provides a split-view playground for testing prompts with:
 * - Variable input forms dynamically generated from prompt variables
 * - Model selector and parameter controls
 * - Split view with rendered prompt on left, LLM output on right
 * - Run button to trigger prompt execution
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { Badge } from '@/components/ui/badge';
import { Loader2, Play, Settings, FileText, Sparkles, Copy, Check } from 'lucide-react';
import { useRenderPrompt, useGeneratePrompt } from '../api/promptApi';
import type {
  PromptVariableDefinition,
  PromptVariableType,
  PromptDetailResponse,
} from '@/types/schemas';
import { toast } from 'sonner';

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
  anthropic: [
    'claude-3-opus-20240229',
    'claude-3-sonnet-20240229',
    'claude-3-haiku-20240307',
  ],
  gemini: ['gemini-pro', 'gemini-ultra'],
  ollama: ['llama3', 'mistral', 'phi3'],
};

interface PromptPlaygroundModalProps {
  prompt: PromptDetailResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface RunConfig {
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
}

const DEFAULT_CONFIG: RunConfig = {
  provider: 'openai',
  model_name: 'gpt-4o',
  temperature: 0.7,
  max_tokens: 1000,
  top_p: 1.0,
  frequency_penalty: 0.0,
  presence_penalty: 0.0,
};

export function PromptPlaygroundModal({
  prompt,
  open,
  onOpenChange,
}: PromptPlaygroundModalProps) {
  const renderMutation = useRenderPrompt();
  const generateMutation = useGeneratePrompt();

  // State for variable values
  const [variableValues, setVariableValues] = useState<Record<string, unknown>>({});
  const [renderedPrompt, setRenderedPrompt] = useState<string>('');
  const [llmOutput, setLlmOutput] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);

  // State for model config
  const [config, setConfig] = useState<RunConfig>(DEFAULT_CONFIG);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // State for copy feedback
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [copiedOutput, setCopiedOutput] = useState(false);

  // Initialize config from prompt
  useEffect(() => {
    if (prompt) {
      setConfig({
        provider: prompt.model_provider || 'openai',
        model_name: prompt.model_name || 'gpt-4o',
        temperature: prompt.temperature ?? 0.7,
        max_tokens: prompt.max_tokens ?? 1000,
        top_p: prompt.top_p ?? 1.0,
        frequency_penalty: prompt.frequency_penalty ?? 0.0,
        presence_penalty: prompt.presence_penalty ?? 0.0,
      });

      // Initialize variable values with defaults
      const initialValues: Record<string, unknown> = {};
      for (const variable of prompt.variables || []) {
        if (variable.default_value !== null && variable.default_value !== undefined) {
          initialValues[variable.name] = variable.default_value;
        } else {
          // Set default based on type
          switch (variable.type) {
            case 'boolean':
              initialValues[variable.name] = false;
              break;
            case 'integer':
              initialValues[variable.name] = 0;
              break;
            case 'float':
              initialValues[variable.name] = 0.0;
              break;
            case 'list':
            case 'dict':
              initialValues[variable.name] = '[]';
              break;
            default:
              initialValues[variable.name] = '';
          }
        }
      }
      setVariableValues(initialValues);
      setRenderedPrompt('');
      setLlmOutput('');
    }
  }, [prompt]);

  // Update variable value
  const updateVariableValue = (name: string, value: unknown) => {
    setVariableValues((prev) => ({ ...prev, [name]: value }));
  };

  // Render the prompt with current variable values
  const handleRender = async () => {
    if (!prompt) return;

    try {
      const variables = Object.entries(variableValues).map(([name, value]) => ({
        name,
        value,
      }));

      const result = await renderMutation.mutateAsync({
        id: prompt.id,
        variables,
        strict: false, // Allow missing variables for testing
      });

      setRenderedPrompt(result.rendered);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to render prompt');
    }
  };

  // Run the full flow: render + LLM generation
  const handleRun = async () => {
    if (!prompt) return;

    setIsRunning(true);
    try {
      // Prepare variables for the API
      const variables = Object.entries(variableValues).map(([name, value]) => ({
        name,
        value,
      }));

      // Call the generate endpoint
      const result = await generateMutation.mutateAsync({
        id: prompt.id,
        variables,
        config: {
          provider: config.provider,
          model_name: config.model_name,
          temperature: config.temperature,
          max_tokens: config.max_tokens,
          top_p: config.top_p,
          frequency_penalty: config.frequency_penalty,
          presence_penalty: config.presence_penalty,
        },
      });

      // Update both rendered prompt and LLM output
      setRenderedPrompt(result.rendered);
      setLlmOutput(result.output);

      toast.success(
        `Generated ${result.total_tokens} tokens in ${result.latency_ms.toFixed(0)}ms`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate prompt');
      // Still render the prompt on error so user can see what they're working with
      await handleRender();
    } finally {
      setIsRunning(false);
    }
  };

  // Copy to clipboard
  const copyToClipboard = async (text: string, type: 'prompt' | 'output') => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'prompt') {
        setCopiedPrompt(true);
        setTimeout(() => setCopiedPrompt(false), 2000);
      } else {
        setCopiedOutput(true);
        setTimeout(() => setCopiedOutput(false), 2000);
      }
      toast.success('Copied to clipboard');
    } catch {
      toast.error('Failed to copy');
    }
  };

  // Update config field
  const updateConfig = <K extends keyof RunConfig>(field: K, value: RunConfig[K]) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  if (!prompt) return null;

  const hasVariables = (prompt.variables || []).length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="h-[85vh] max-w-6xl gap-0 p-0">
        <DialogHeader className="border-b px-6 pb-4 pt-6">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-xl">Prompt Playground</DialogTitle>
              <DialogDescription className="mt-1">
                Test your prompt with variables and see the rendered output
              </DialogDescription>
            </div>
            <Button onClick={handleRun} disabled={isRunning} className="gap-2">
              {isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Run Prompt
            </Button>
          </div>
        </DialogHeader>

        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel - Variables and Config */}
          <div className="flex w-[400px] flex-col overflow-hidden border-r">
            <ScrollArea className="flex-1 px-6 py-4">
              {/* Variables Section */}
              {hasVariables && (
                <div className="mb-6">
                  <div className="mb-4 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <h3 className="font-semibold">Variables</h3>
                  </div>

                  <div className="space-y-4">
                    {prompt.variables?.map((variable) => (
                      <VariableInput
                        key={variable.name}
                        variable={variable}
                        value={variableValues[variable.name]}
                        onChange={(value) => updateVariableValue(variable.name, value)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {!hasVariables && (
                <div className="mb-6 rounded-md border bg-muted/50 p-4">
                  <p className="text-center text-sm text-muted-foreground">
                    This prompt has no variables defined.
                  </p>
                </div>
              )}

              <Separator className="my-4" />

              {/* Model Config Section */}
              <div>
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Settings className="h-4 w-4 text-muted-foreground" />
                    <h3 className="font-semibold">Model Configuration</h3>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-xs"
                  >
                    {showAdvanced ? 'Less' : 'More'}
                  </Button>
                </div>

                <div className="space-y-4">
                  {/* Provider */}
                  <div className="space-y-2">
                    <Label>Provider</Label>
                    <Select
                      value={config.provider}
                      onValueChange={(value) => {
                        updateConfig('provider', value);
                        const suggestions = MODEL_SUGGESTIONS[value];
                        if (suggestions && suggestions.length > 0) {
                          updateConfig('model_name', suggestions[0] ?? 'gpt-4o');
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
                      value={config.model_name}
                      onValueChange={(value) => updateConfig('model_name', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(MODEL_SUGGESTIONS[config.provider] || []).map((model) => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Temperature */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm">Temperature</Label>
                      <span className="text-xs text-muted-foreground">
                        {config.temperature.toFixed(2)}
                      </span>
                    </div>
                    <Slider
                      value={[config.temperature]}
                      onValueChange={([value]) =>
                        updateConfig('temperature', value ?? 0.7)
                      }
                      min={0}
                      max={2}
                      step={0.1}
                      className="w-full"
                    />
                  </div>

                  {/* Max Tokens */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm">Max Tokens</Label>
                      <span className="text-xs text-muted-foreground">
                        {config.max_tokens}
                      </span>
                    </div>
                    <Slider
                      value={[config.max_tokens]}
                      onValueChange={([value]) =>
                        updateConfig('max_tokens', value ?? 1000)
                      }
                      min={100}
                      max={8000}
                      step={100}
                      className="w-full"
                    />
                  </div>

                  {/* Advanced Settings */}
                  {showAdvanced && (
                    <>
                      <Separator className="my-2" />

                      {/* Top P */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-sm">Top P</Label>
                          <span className="text-xs text-muted-foreground">
                            {config.top_p.toFixed(2)}
                          </span>
                        </div>
                        <Slider
                          value={[config.top_p]}
                          onValueChange={([value]) =>
                            updateConfig('top_p', value ?? 1.0)
                          }
                          min={0}
                          max={1}
                          step={0.05}
                          className="w-full"
                        />
                      </div>

                      {/* Frequency Penalty */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-sm">Frequency Penalty</Label>
                          <span className="text-xs text-muted-foreground">
                            {config.frequency_penalty.toFixed(2)}
                          </span>
                        </div>
                        <Slider
                          value={[config.frequency_penalty]}
                          onValueChange={([value]) =>
                            updateConfig('frequency_penalty', value ?? 0.0)
                          }
                          min={-2}
                          max={2}
                          step={0.1}
                          className="w-full"
                        />
                      </div>

                      {/* Presence Penalty */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-sm">Presence Penalty</Label>
                          <span className="text-xs text-muted-foreground">
                            {config.presence_penalty.toFixed(2)}
                          </span>
                        </div>
                        <Slider
                          value={[config.presence_penalty]}
                          onValueChange={([value]) =>
                            updateConfig('presence_penalty', value ?? 0.0)
                          }
                          min={-2}
                          max={2}
                          step={0.1}
                          className="w-full"
                        />
                      </div>
                    </>
                  )}
                </div>
              </div>
            </ScrollArea>
          </div>

          {/* Right Panel - Split View */}
          <div className="flex flex-1">
            {/* Rendered Prompt */}
            <div className="flex flex-1 flex-col overflow-hidden border-r">
              <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <h4 className="text-sm font-medium">Rendered Prompt</h4>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    copyToClipboard(renderedPrompt || prompt.content, 'prompt')
                  }
                  disabled={!renderedPrompt && !prompt.content}
                  className="h-7 text-xs"
                >
                  {copiedPrompt ? (
                    <>
                      <Check className="mr-1 h-3 w-3" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="mr-1 h-3 w-3" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
              <ScrollArea className="flex-1 p-4">
                {renderedPrompt ? (
                  <pre className="whitespace-pre-wrap break-words font-mono text-sm">
                    {renderedPrompt}
                  </pre>
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    Click "Run Prompt" to see the rendered output
                  </div>
                )}
              </ScrollArea>
            </div>

            {/* LLM Output */}
            <div className="flex flex-1 flex-col overflow-hidden">
              <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-muted-foreground" />
                  <h4 className="text-sm font-medium">LLM Output</h4>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(llmOutput, 'output')}
                  disabled={!llmOutput}
                  className="h-7 text-xs"
                >
                  {copiedOutput ? (
                    <>
                      <Check className="mr-1 h-3 w-3" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="mr-1 h-3 w-3" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
              <ScrollArea className="flex-1 p-4">
                {llmOutput ? (
                  <div className="whitespace-pre-wrap break-words text-sm">
                    {llmOutput}
                  </div>
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    LLM output will appear here after running the prompt
                  </div>
                )}
              </ScrollArea>
            </div>
          </div>
        </div>

        {/* Footer with stats */}
        <div className="border-t bg-muted/30 px-6 py-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <span>{prompt.name}</span>
              <Separator orientation="vertical" className="h-4" />
              <span>v{prompt.version}</span>
              {prompt.tags.length > 0 && (
                <>
                  <Separator orientation="vertical" className="h-4" />
                  <div className="flex gap-1">
                    {prompt.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="outline" className="py-0 text-xs">
                        {tag}
                      </Badge>
                    ))}
                    {prompt.tags.length > 3 && (
                      <Badge variant="outline" className="py-0 text-xs">
                        +{prompt.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                </>
              )}
            </div>
            <div>
              {renderedPrompt && llmOutput && (
                <span>
                  ~{Math.ceil(renderedPrompt.length / 4)} in, ~
                  {Math.ceil(llmOutput.length / 4)} out
                </span>
              )}
              {renderedPrompt && !llmOutput && (
                <span>~{Math.ceil(renderedPrompt.length / 4)} tokens</span>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface VariableInputProps {
  variable: PromptVariableDefinition;
  value: unknown;
  onChange: (value: unknown) => void;
}

function VariableInput({ variable, value, onChange }: VariableInputProps) {
  const handleInputChange = (newValue: string) => {
    switch (variable.type) {
      case 'string':
        onChange(newValue);
        break;
      case 'integer':
        onChange(parseInt(newValue, 10) || 0);
        break;
      case 'float':
        onChange(parseFloat(newValue) || 0.0);
        break;
      case 'boolean':
        onChange(newValue === 'true');
        break;
      case 'list':
      case 'dict':
        // Parse as JSON for list/dict types
        try {
          onChange(JSON.parse(newValue));
        } catch {
          onChange(newValue);
        }
        break;
    }
  };

  const renderInput = () => {
    switch (variable.type) {
      case 'boolean':
        return (
          <div className="flex items-center gap-2">
            <Switch
              checked={Boolean(value)}
              onCheckedChange={(checked) => onChange(checked)}
            />
            <span className="text-sm text-muted-foreground">
              {value ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        );

      case 'integer':
      case 'float':
        return (
          <Input
            type="number"
            step={variable.type === 'float' ? 0.01 : 1}
            value={String(value ?? '')}
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder={variable.type === 'float' ? '0.0' : '0'}
          />
        );

      case 'list':
      case 'dict':
        return (
          <Textarea
            value={
              typeof value === 'string' ? value : JSON.stringify(value ?? '', null, 2)
            }
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder={
              variable.type === 'list' ? '["item1", "item2"]' : '{"key": "value"}'
            }
            className="font-mono text-xs"
            rows={3}
          />
        );

      default: // string
        return (
          <Textarea
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value)}
            placeholder={`Enter ${variable.name}`}
            rows={variable.description ? 4 : 2}
          />
        );
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm">
          {variable.name}
          {variable.required && <span className="ml-1 text-destructive">*</span>}
        </Label>
        <Badge variant="outline" className="py-0 text-xs">
          {VARIABLE_TYPES.find((t) => t.value === variable.type)?.label ||
            variable.type}
        </Badge>
      </div>
      {renderInput()}
      {variable.description && (
        <p className="text-xs text-muted-foreground">{variable.description}</p>
      )}
    </div>
  );
}
