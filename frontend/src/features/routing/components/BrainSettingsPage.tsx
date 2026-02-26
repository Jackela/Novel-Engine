/**
 * Brain Settings Page - Model Routing Configuration
 *
 * BRAIN-028B: Model Routing Configuration
 * BRAIN-033: Brain Settings UI
 * BRAIN-035A: Token Usage Analytics Dashboard
 *
 * Manages AI Brain settings including:
 * - Model routing preferences per task type
 * - Circuit breaker configuration
 * - Routing constraints and fallback settings
 * - API Keys management
 * - RAG configuration
 * - Knowledge base status
 * - Token usage and cost analytics
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { brainSettingsApi } from '@/features/routing/api/brainSettingsApi';
import { routingApi } from '@/features/routing/api/routingApi';
import {
  ApiKeyPanel,
  ModelConfigPanel,
  RagConfigPanel,
  TokenAnalyticsPanel,
} from './panels';
import { RefreshCw, Settings2 } from 'lucide-react';

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
  anthropic: [
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022',
    'claude-3-opus-20240229',
  ],
  gemini: ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-1.5-flash'],
  ollama: ['llama3.2', 'mistral', 'phi3'],
  mock: ['mock-model'],
};

export { TASK_LABELS, TASK_DESCRIPTIONS, PROVIDER_LABELS, PROVIDER_MODELS };
export type { TaskRule, RoutingConstraints, RoutingConfig, RAGConfigData };

export function BrainSettingsPage() {
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
    refetchInterval: 30000,
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

  const handleRefetchAll = () => {
    refetchConfig();
    refetchStats();
    refetchBrainSettings();
  };

  if (configLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="h-10 w-48 animate-pulse rounded bg-muted" />
          <div className="mt-2 h-5 w-96 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="h-64 animate-pulse rounded bg-muted" />
          <div className="h-64 animate-pulse rounded bg-muted" />
        </div>
      </div>
    );
  }

  if (configError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">
              Failed to load configuration
            </CardTitle>
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
    <div className="container mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold">
            <Settings2 className="h-8 w-8" />
            Brain Settings
          </h1>
          <p className="mt-2 text-muted-foreground">
            Configure AI model routing, circuit breakers, and fallback preferences
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefetchAll} size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs defaultValue="routing" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5 lg:w-auto">
          <TabsTrigger value="routing">Model Config</TabsTrigger>
          <TabsTrigger value="usage">Usage</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="rag-settings">RAG Settings</TabsTrigger>
        </TabsList>

        {/* Model Config Tab - Combines routing, constraints, circuits, and stats */}
        <TabsContent value="routing" className="space-y-6">
          <ModelConfigPanel
            config={config}
            stats={stats}
            statsLoading={statsLoading}
            isSaving={isSaving}
            onSaveComplete={handleRefetchAll}
            onSavingChange={setIsSaving}
          />
        </TabsContent>

        {/* Usage Analytics Tab */}
        <TabsContent value="usage" className="space-y-6">
          <TokenAnalyticsPanel />
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-6">
          <ApiKeyPanel
            brainSettings={brainSettings}
            brainSettingsLoading={brainSettingsLoading}
            isSaving={isSaving}
            onSaveComplete={handleRefetchAll}
            onSavingChange={setIsSaving}
          />
        </TabsContent>

        {/* RAG Settings Tab */}
        <TabsContent value="rag-settings" className="space-y-6">
          <RagConfigPanel
            brainSettings={brainSettings}
            isSaving={isSaving}
            onSaveComplete={handleRefetchAll}
            onSavingChange={setIsSaving}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Export as default for page wrapper
export default BrainSettingsPage;
