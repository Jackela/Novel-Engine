/**
 * Brain Settings Page - Model Routing Configuration
 *
 * BRAIN-028B: Model Routing Configuration
 * BRAIN-033: Brain Settings UI
 *
 * Manages AI Brain settings including:
 * - Model routing preferences per task type
 * - Circuit breaker configuration
 * - Routing constraints and fallback settings
 * - API Keys management
 * - RAG configuration
 * - Knowledge base status
 */

import { useQuery } from '@tanstack/react-query';
import {
  CheckCircle2,
  Database,
  Eye,
  EyeOff,
  Key,
  RefreshCw,
  Settings2,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { brainSettingsApi } from '@/features/routing/api/brainSettingsApi';
import { routingApi } from '@/features/routing/api/routingApi';

// Types for brain settings
interface RAGConfigData {
  enabled: boolean;
  max_chunks: number;
  score_threshold: number;
  context_token_limit: number;
  include_sources: boolean;
  chunk_size: number;
  chunk_overlap: number;
  hybrid_search_weight: number;
}

type TaskType = 'creative' | 'logical' | 'fast' | 'cheap';
type Provider = 'openai' | 'anthropic' | 'gemini' | 'ollama' | 'mock';

interface TaskRule {
  task_type: string;
  provider: string;
  model_name: string;
  temperature: number | null;
  max_tokens: number | null;
  priority: number;
  enabled: boolean;
}

interface RoutingConstraints {
  max_cost_per_1m_tokens: number | null;
  max_latency_ms: number | null;
  preferred_providers: string[];
  blocked_providers: string[];
  require_capabilities: string[];
}

interface RoutingConfig {
  workspace_id: string;
  scope: string;
  task_rules: TaskRule[];
  constraints: RoutingConstraints | null;
  circuit_breaker_rules: Array<{
    model_key: string;
    failure_threshold: number;
    timeout_seconds: number;
    enabled: boolean;
  }>;
  enable_circuit_breaker: boolean;
  enable_fallback: boolean;
  created_at: string;
  updated_at: string;
  version: number;
}

const TASK_LABELS: Record<TaskType, string> = {
  creative: 'Creative',
  logical: 'Logical',
  fast: 'Fast',
  cheap: 'Cheap',
};

const TASK_DESCRIPTIONS: Record<TaskType, string> = {
  creative: 'Creative writing, dialogue generation (high temperature)',
  logical: 'Analysis, structured output (low temperature)',
  fast: 'Quick operations, autocomplete (speed focused)',
  cheap: 'Cost-sensitive operations (low-cost models)',
};

const PROVIDER_LABELS: Record<Provider, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  ollama: 'Ollama (Local)',
  mock: 'Mock',
};

const PROVIDER_MODELS: Record<Provider, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
  gemini: ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-1.5-flash'],
  ollama: ['llama3.2', 'mistral', 'phi3'],
  mock: ['mock-model'],
};

export function BrainSettingsPage() {
  // Simple toast notification helper (replace with useToast if available)
  const toast = ({ title, description, variant = 'default' }: { title: string; description?: string; variant?: 'default' }) => {
    console.log(`[${variant.toUpperCase()}] ${title}: ${description}`);
  };

  const [isSaving, setIsSaving] = useState(false);

  // Fetch routing configuration
  const {
    data: config,
    isLoading: configLoading,
    error: configError,
    refetch: refetchConfig,
  } = useQuery({
    queryKey: ['routing-config', 'global'],
    queryFn: () => routingApi.getConfig(undefined),
  });

  // Fetch routing stats
  const {
    data: stats,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['routing-stats'],
    queryFn: () => routingApi.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // BRAIN-033: Fetch brain settings data
  const {
    data: brainSettings,
    isLoading: brainSettingsLoading,
    refetch: refetchBrainSettings,
  } = useQuery({
    queryKey: ['brain-settings'],
    queryFn: () => brainSettingsApi.getSettings(),
  });

  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [localKeys, setLocalKeys] = useState<Record<string, string>>({
    openai: '',
    anthropic: '',
    gemini: '',
  });
  const [localOllamaUrl, setLocalOllamaUrl] = useState('http://localhost:11434');

  const handleSaveAPIKey = async (provider: string, key: string) => {
    setIsSaving(true);
    try {
      await brainSettingsApi.updateAPIKeys({ [`${provider}_key`]: key || null });
      await refetchBrainSettings();
      setLocalKeys({ ...localKeys, [provider]: '' });
      toast({
        title: 'API Key saved',
        description: `${provider.charAt(0).toUpperCase() + provider.slice(1)} API key has been updated.`,
      });
    } catch (error) {
      toast({
        title: 'Failed to save',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveOllamaUrl = async (url: string) => {
    setIsSaving(true);
    try {
      await brainSettingsApi.updateAPIKeys({ ollama_base_url: url });
      await refetchBrainSettings();
      toast({
        title: 'Ollama URL saved',
        description: 'Ollama base URL has been updated.',
      });
    } catch (error) {
      toast({
        title: 'Failed to save',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveRAGConfig = async (updates: Partial<RAGConfigData>) => {
    setIsSaving(true);
    try {
      await brainSettingsApi.updateRAGConfig(updates);
      await refetchBrainSettings();
      toast({
        title: 'RAG configuration saved',
        description: 'Your RAG settings have been updated.',
      });
    } catch (error) {
      toast({
        title: 'Failed to save',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveConfig = async (updates: Partial<RoutingConfig>) => {
    if (!config) return;

    setIsSaving(true);
    try {
      await routingApi.updateConfig(undefined, updates);
      await refetchConfig();
      toast({
        title: 'Configuration saved',
        description: 'Your routing preferences have been updated.',
      });
    } catch (error) {
      toast({
        title: 'Failed to save',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetCircuitBreaker = async (modelKey: string) => {
    try {
      await routingApi.resetCircuitBreaker(modelKey);
      await refetchStats();
      toast({
        title: 'Circuit breaker reset',
        description: `Circuit breaker for ${modelKey} has been reset.`,
      });
    } catch (error) {
      toast({
        title: 'Failed to reset',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const TaskRuleCard = ({ rule, taskType }: { rule: TaskRule | undefined; taskType: TaskType }) => {
    const [localProvider, setLocalProvider] = useState<Provider>(
      (rule?.provider as Provider) || 'gemini'
    );
    const [localModel, setLocalModel] = useState(rule?.model_name || '');
    const [localTemp, setLocalTemp] = useState(rule?.temperature ?? null);
    const [localMaxTokens, setLocalMaxTokens] = useState(rule?.max_tokens ?? null);
    const [localEnabled, setLocalEnabled] = useState(rule?.enabled ?? true);

    const availableModels = PROVIDER_MODELS[localProvider];

    const handleSave = () => {
      const updatedRules = config?.task_rules.map((r) =>
        r.task_type === taskType
          ? {
              ...r,
              provider: localProvider,
              model_name: localModel,
              temperature: localTemp,
              max_tokens: localMaxTokens,
              enabled: localEnabled,
            }
          : r
      ) || [];

      const newRule: TaskRule = {
        task_type: taskType,
        provider: localProvider,
        model_name: localModel,
        temperature: localTemp,
        max_tokens: localMaxTokens,
        priority: rule?.priority || 0,
        enabled: localEnabled,
      };

      const existingRuleIndex = updatedRules.findIndex((r) => r.task_type === taskType);
      if (existingRuleIndex >= 0) {
        updatedRules[existingRuleIndex] = newRule;
      } else {
        updatedRules.push(newRule);
      }

      handleSaveConfig({ task_rules: updatedRules });
    };

    return (
      <Card className={!localEnabled ? 'opacity-60' : ''}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">{TASK_LABELS[taskType]}</CardTitle>
              <CardDescription className="text-xs">{TASK_DESCRIPTIONS[taskType]}</CardDescription>
            </div>
            <Switch checked={localEnabled} onCheckedChange={setLocalEnabled} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor={`provider-${taskType}`}>Provider</Label>
              <Select
                value={localProvider}
                onValueChange={(v) => {
                  setLocalProvider(v as Provider);
                  setLocalModel('');
                }}
                disabled={!localEnabled}
              >
                <SelectTrigger id={`provider-${taskType}`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PROVIDER_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor={`model-${taskType}`}>Model</Label>
              <Select
                value={localModel || 'default'}
                onValueChange={(v) => setLocalModel(v === 'default' ? '' : v)}
                disabled={!localEnabled || !localProvider}
              >
                <SelectTrigger id={`model-${taskType}`}>
                  <SelectValue placeholder="Provider default" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Provider default</SelectItem>
                  {availableModels.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor={`temp-${taskType}`}>Temperature</Label>
              <Input
                id={`temp-${taskType}`}
                type="number"
                step="0.1"
                min="0"
                max="2"
                placeholder="Default"
                value={localTemp ?? ''}
                onChange={(e) => setLocalTemp(e.target.value ? parseFloat(e.target.value) : null)}
                disabled={!localEnabled}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor={`tokens-${taskType}`}>Max Tokens</Label>
              <Input
                id={`tokens-${taskType}`}
                type="number"
                min="1"
                placeholder="Default"
                value={localMaxTokens ?? ''}
                onChange={(e) => setLocalMaxTokens(e.target.value ? parseInt(e.target.value, 10) : null)}
                disabled={!localEnabled}
              />
            </div>
          </div>

          <div className="flex justify-end">
            <Button size="sm" onClick={handleSave} disabled={!localEnabled || isSaving}>
              {isSaving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  if (configLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <div className="h-10 w-48 bg-muted animate-pulse rounded" />
          <div className="mt-2 h-5 w-96 bg-muted animate-pulse rounded" />
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="h-64 bg-muted animate-pulse rounded" />
          <div className="h-64 bg-muted animate-pulse rounded" />
        </div>
      </div>
    );
  }

  if (configError) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Failed to load configuration</CardTitle>
            <CardDescription>
              {configError instanceof Error ? configError.message : 'Unknown error'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => refetchConfig()}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Settings2 className="w-8 h-8" />
            Brain Settings
          </h1>
          <p className="text-muted-foreground mt-2">
            Configure AI model routing, circuit breakers, and fallback preferences
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetchConfig()} size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs defaultValue="routing" className="space-y-6">
        <TabsList className="grid w-full grid-cols-6 lg:w-auto">
          <TabsTrigger value="routing">Model Routing</TabsTrigger>
          <TabsTrigger value="constraints">Constraints</TabsTrigger>
          <TabsTrigger value="circuits">Circuit Breakers</TabsTrigger>
          <TabsTrigger value="stats">Statistics</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="rag-settings">RAG Settings</TabsTrigger>
        </TabsList>

        {/* Model Routing Tab */}
        <TabsContent value="routing" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Global Settings</CardTitle>
              <CardDescription>Apply to all routing decisions</CardDescription>
            </CardHeader>
            <CardContent className="flex gap-6">
              <div className="flex items-center justify-between">
                <Label htmlFor="enable-fallback">Enable Fallback Chain</Label>
                <Switch
                  id="enable-fallback"
                  checked={config?.enable_fallback ?? true}
                  onCheckedChange={(checked) => handleSaveConfig({ enable_fallback: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="enable-circuit">Enable Circuit Breaker</Label>
                <Switch
                  id="enable-circuit"
                  checked={config?.enable_circuit_breaker ?? true}
                  onCheckedChange={(checked) => handleSaveConfig({ enable_circuit_breaker: checked })}
                />
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Task-Based Routing</h2>
            <p className="text-muted-foreground text-sm">
              Configure which model to use for each type of task. Higher priority rules take precedence.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {(['creative', 'logical', 'fast', 'cheap'] as TaskType[]).map((taskType) => {
                const rule = config?.task_rules.find((r) => r.task_type === taskType);
                return <TaskRuleCard key={taskType} rule={rule} taskType={taskType} />;
              })}
            </div>
          </div>
        </TabsContent>

        {/* Constraints Tab */}
        <TabsContent value="constraints" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Routing Constraints</CardTitle>
              <CardDescription>
                Limit which models can be selected based on cost, latency, and other factors
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="max-cost">Maximum Cost (per 1M tokens)</Label>
                <Input
                  id="max-cost"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="No limit"
                  value={config?.constraints?.max_cost_per_1m_tokens ?? ''}
                  onChange={(e) =>
                    handleSaveConfig({
                      constraints: {
                        ...config?.constraints,
                        max_cost_per_1m_tokens: e.target.value ? parseFloat(e.target.value) : null,
                      } as RoutingConstraints,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max-latency">Maximum Latency (ms)</Label>
                <Input
                  id="max-latency"
                  type="number"
                  min="0"
                  placeholder="No limit"
                  value={config?.constraints?.max_latency_ms ?? ''}
                  onChange={(e) =>
                    handleSaveConfig({
                      constraints: {
                        ...config?.constraints,
                        max_latency_ms: e.target.value ? parseInt(e.target.value, 10) : null,
                      } as RoutingConstraints,
                    })
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Provider Preferences</CardTitle>
              <CardDescription>Order providers by preference for routing decisions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(PROVIDER_LABELS).map(([value, label]) => {
                  const isBlocked = config?.constraints?.blocked_providers?.includes(value);
                  return (
                    <div key={value} className="flex items-center justify-between p-2 border rounded">
                      <span>{label}</span>
                      <Switch
                        checked={!isBlocked}
                        onCheckedChange={(checked) => {
                          const currentBlocked = config?.constraints?.blocked_providers || [];
                          const newBlocked = checked
                            ? currentBlocked.filter((p) => p !== value)
                            : [...currentBlocked, value];
                          handleSaveConfig({
                            constraints: {
                              ...config?.constraints,
                              blocked_providers: newBlocked,
                            } as RoutingConstraints,
                          });
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Circuit Breakers Tab */}
        <TabsContent value="circuits" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Circuit Breaker Status</CardTitle>
              <CardDescription>
                Circuit breakers prevent cascading failures by temporarily disabling failing models
              </CardDescription>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="h-32 bg-muted animate-pulse rounded" />
              ) : stats?.open_circuits && stats.open_circuits.length > 0 ? (
                <div className="space-y-2">
                  {stats.open_circuits.map((circuit) => (
                    <div
                      key={circuit.model}
                      className="flex items-center justify-between p-3 border border-destructive rounded destructive/10"
                    >
                      <div>
                        <div className="font-medium">{circuit.model}</div>
                        <div className="text-sm text-muted-foreground">
                          Failures: {circuit.failure_count} | State: {circuit.state}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleResetCircuitBreaker(circuit.model)}
                      >
                        Reset
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No open circuits. All models are healthy.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Circuit Breaker Configuration</CardTitle>
              <CardDescription>Configure thresholds and timeouts for specific models</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-sm">
                Circuit breaker rules can be configured per model. Default: 5 failures triggers timeout,
                60 seconds before retry.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Statistics Tab */}
        <TabsContent value="stats" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Decisions</CardDescription>
                <CardTitle className="text-2xl">
                  {statsLoading ? '...' : stats?.total_decisions.toLocaleString() ?? 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Fallback Rate</CardDescription>
                <CardTitle className="text-2xl">
                  {statsLoading ? '...' : `${((stats?.fallback_rate ?? 0) * 100).toFixed(1)}%`}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg Routing Time</CardDescription>
                <CardTitle className="text-2xl">
                  {statsLoading ? '...' : `${stats?.avg_routing_time_ms.toFixed(2)}ms`}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Active Circuits</CardDescription>
                <CardTitle className="text-2xl">
                  {statsLoading ? '...' : stats?.open_circuits.length ?? 0}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Provider Usage</CardTitle>
              <CardDescription>Number of requests routed to each provider</CardDescription>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="h-32 bg-muted animate-pulse rounded" />
              ) : (
                <div className="space-y-2">
                  {Object.entries(stats?.provider_counts || {}).map(([provider, count]) => (
                    <div key={provider} className="flex items-center gap-2">
                      <span className="w-24 text-sm">{PROVIDER_LABELS[provider as Provider] || provider}</span>
                      <div className="flex-1 bg-muted rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full"
                          style={{
                            width: `${(count / (stats?.total_decisions || 1)) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="w-12 text-sm text-right">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Routing Reasons</CardTitle>
              <CardDescription>Why models were selected for routing</CardDescription>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="h-32 bg-muted animate-pulse rounded" />
              ) : (
                <div className="space-y-2">
                  {Object.entries(stats?.reason_counts || {}).map(([reason, count]) => (
                    <div key={reason} className="flex items-center justify-between p-2 border rounded">
                      <span className="capitalize text-sm">{reason.replace(/_/g, ' ')}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* BRAIN-033: API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="w-5 h-5" />
                API Keys
              </CardTitle>
              <CardDescription>
                Configure API keys for LLM providers. Keys are encrypted and stored securely.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Knowledge Base Status */}
              <div className="border rounded-lg p-4 bg-muted/50">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Knowledge Base Status
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <div className="text-2xl font-bold">
                      {brainSettingsLoading ? '...' : brainSettings?.knowledge_base.total_entries ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Total Entries</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">
                      {brainSettingsLoading ? '...' : brainSettings?.knowledge_base.characters_count ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Characters</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">
                      {brainSettingsLoading ? '...' : brainSettings?.knowledge_base.lore_count ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Lore</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">
                      {brainSettingsLoading ? '...' : brainSettings?.knowledge_base.scenes_count ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Scenes</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">
                      {brainSettings?.knowledge_base.is_healthy ? (
                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                      ) : (
                        <XCircle className="w-6 h-6 text-red-500" />
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">Health</div>
                  </div>
                </div>
              </div>

              {/* OpenAI API Key */}
              <div className="space-y-3">
                <Label htmlFor="openai-key" className="flex items-center gap-2">
                  <span>OpenAI API Key</span>
                  {brainSettings?.api_keys.has_openai && (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  )}
                </Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      id="openai-key"
                      type={visibleKeys.openai ? 'text' : 'password'}
                      placeholder={brainSettings?.api_keys.has_openai ? brainSettings.api_keys.openai_key : 'sk-...'}
                      value={localKeys.openai || ''}
                      onChange={(e) => setLocalKeys({ ...localKeys, openai: e.target.value || '' })}
                      className="pr-20"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 px-2"
                      onClick={() => setVisibleKeys({ ...visibleKeys, openai: !visibleKeys.openai })}
                    >
                      {visibleKeys.openai ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => handleSaveAPIKey('openai', localKeys.openai || '')}
                    disabled={!localKeys.openai || isSaving}
                  >
                    Save
                  </Button>
                </div>
              </div>

              {/* Anthropic API Key */}
              <div className="space-y-3">
                <Label htmlFor="anthropic-key" className="flex items-center gap-2">
                  <span>Anthropic API Key</span>
                  {brainSettings?.api_keys.has_anthropic && (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  )}
                </Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      id="anthropic-key"
                      type={visibleKeys.anthropic ? 'text' : 'password'}
                      placeholder={brainSettings?.api_keys.has_anthropic ? brainSettings.api_keys.anthropic_key : 'sk-ant-...'}
                      value={localKeys.anthropic || ''}
                      onChange={(e) => setLocalKeys({ ...localKeys, anthropic: e.target.value || '' })}
                      className="pr-20"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 px-2"
                      onClick={() => setVisibleKeys({ ...visibleKeys, anthropic: !visibleKeys.anthropic })}
                    >
                      {visibleKeys.anthropic ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => handleSaveAPIKey('anthropic', localKeys.anthropic || '')}
                    disabled={!localKeys.anthropic || isSaving}
                  >
                    Save
                  </Button>
                </div>
              </div>

              {/* Gemini API Key */}
              <div className="space-y-3">
                <Label htmlFor="gemini-key" className="flex items-center gap-2">
                  <span>Google Gemini API Key</span>
                  {brainSettings?.api_keys.has_gemini && (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  )}
                </Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      id="gemini-key"
                      type={visibleKeys.gemini ? 'text' : 'password'}
                      placeholder={brainSettings?.api_keys.has_gemini ? brainSettings.api_keys.gemini_key : 'AIza-...'}
                      value={localKeys.gemini || ''}
                      onChange={(e) => setLocalKeys({ ...localKeys, gemini: e.target.value || '' })}
                      className="pr-20"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 px-2"
                      onClick={() => setVisibleKeys({ ...visibleKeys, gemini: !visibleKeys.gemini })}
                    >
                      {visibleKeys.gemini ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => handleSaveAPIKey('gemini', localKeys.gemini || '')}
                    disabled={!localKeys.gemini || isSaving}
                  >
                    Save
                  </Button>
                </div>
              </div>

              {/* Ollama Base URL */}
              <div className="space-y-3">
                <Label htmlFor="ollama-url">Ollama Base URL</Label>
                <div className="flex gap-2">
                  <Input
                    id="ollama-url"
                    type="text"
                    placeholder="http://localhost:11434"
                    value={localOllamaUrl}
                    onChange={(e) => setLocalOllamaUrl(e.target.value)}
                  />
                  <Button
                    size="sm"
                    onClick={() => handleSaveOllamaUrl(localOllamaUrl)}
                    disabled={isSaving}
                  >
                    Save
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  For local models using Ollama. Leave default unless running Ollama on a different host.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* BRAIN-033: RAG Settings Tab */}
        <TabsContent value="rag-settings" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5" />
                RAG Configuration
              </CardTitle>
              <CardDescription>
                Configure retrieval-augmented generation settings for knowledge base queries.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Enable RAG */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <Label htmlFor="rag-enabled" className="text-base">Enable RAG</Label>
                  <p className="text-sm text-muted-foreground">
                    Use knowledge base context when generating responses
                  </p>
                </div>
                <Switch
                  id="rag-enabled"
                  checked={brainSettings?.rag_config.enabled ?? true}
                  onCheckedChange={(checked) => handleSaveRAGConfig({ enabled: checked })}
                />
              </div>

              {/* Chunk Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Chunking Settings</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="chunk-size">Chunk Size</Label>
                    <Input
                      id="chunk-size"
                      type="number"
                      min={100}
                      max={10000}
                      value={brainSettings?.rag_config.chunk_size ?? 500}
                      onChange={(e) => handleSaveRAGConfig({ chunk_size: parseInt(e.target.value, 10) })}
                    />
                    <p className="text-xs text-muted-foreground">Default: 500 tokens</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="chunk-overlap">Chunk Overlap</Label>
                    <Input
                      id="chunk-overlap"
                      type="number"
                      min={0}
                      max={1000}
                      value={brainSettings?.rag_config.chunk_overlap ?? 50}
                      onChange={(e) => handleSaveRAGConfig({ chunk_overlap: parseInt(e.target.value, 10) })}
                    />
                    <p className="text-xs text-muted-foreground">Default: 50 tokens</p>
                  </div>
                </div>
              </div>

              {/* Retrieval Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Retrieval Settings</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max-chunks">Max Chunks</Label>
                    <Input
                      id="max-chunks"
                      type="number"
                      min={1}
                      max={50}
                      value={brainSettings?.rag_config.max_chunks ?? 5}
                      onChange={(e) => handleSaveRAGConfig({ max_chunks: parseInt(e.target.value, 10) })}
                    />
                    <p className="text-xs text-muted-foreground">Maximum chunks to retrieve</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="score-threshold">Score Threshold</Label>
                    <Input
                      id="score-threshold"
                      type="number"
                      min={0}
                      max={1}
                      step={0.1}
                      value={brainSettings?.rag_config.score_threshold ?? 0}
                      onChange={(e) => handleSaveRAGConfig({ score_threshold: parseFloat(e.target.value) })}
                    />
                    <p className="text-xs text-muted-foreground">Minimum relevance score (0-1)</p>
                  </div>
                </div>
              </div>

              {/* Hybrid Search Weight */}
              <div className="space-y-2">
                <Label htmlFor="hybrid-weight">Hybrid Search Weight</Label>
                <div className="flex items-center gap-4">
                  <Input
                    id="hybrid-weight"
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    className="flex-1"
                    value={brainSettings?.rag_config.hybrid_search_weight ?? 0.7}
                    onChange={(e) => handleSaveRAGConfig({ hybrid_search_weight: parseFloat(e.target.value) })}
                  />
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    Vector: {Math.round((brainSettings?.rag_config.hybrid_search_weight ?? 0.7) * 100)}% / BM25: {Math.round((1 - (brainSettings?.rag_config.hybrid_search_weight ?? 0.7)) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Balance between semantic (vector) and keyword (BM25) search
                </p>
              </div>

              {/* Context Token Limit */}
              <div className="space-y-2">
                <Label htmlFor="token-limit">Context Token Limit</Label>
                <Input
                  id="token-limit"
                  type="number"
                  min={100}
                  max={100000}
                  value={brainSettings?.rag_config.context_token_limit ?? 4000}
                  onChange={(e) => handleSaveRAGConfig({ context_token_limit: parseInt(e.target.value, 10) })}
                />
                <p className="text-xs text-muted-foreground">
                  Maximum tokens for retrieved context (default: 4000)
                </p>
              </div>

              {/* Include Sources */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <Label htmlFor="include-sources" className="text-base">Include Source Citations</Label>
                  <p className="text-sm text-muted-foreground">
                    Add source references to retrieved context
                  </p>
                </div>
                <Switch
                  id="include-sources"
                  checked={brainSettings?.rag_config.include_sources ?? true}
                  onCheckedChange={(checked) => handleSaveRAGConfig({ include_sources: checked })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Export as default for page wrapper
export default BrainSettingsPage;
