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
 */

import { useQuery } from '@tanstack/react-query';
import { RefreshCw, Settings2 } from 'lucide-react';
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
import { routingApi } from '@/features/routing/api/routingApi';

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
        <TabsList>
          <TabsTrigger value="routing">Model Routing</TabsTrigger>
          <TabsTrigger value="constraints">Constraints</TabsTrigger>
          <TabsTrigger value="circuits">Circuit Breakers</TabsTrigger>
          <TabsTrigger value="stats">Statistics</TabsTrigger>
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
      </Tabs>
    </div>
  );
}

// Export as default for page wrapper
export default BrainSettingsPage;
