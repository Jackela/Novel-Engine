/**
 * RagConfigPanel - RAG configuration settings
 *
 * BRAIN-033: Brain Settings UI
 *
 * Manages retrieval-augmented generation settings for knowledge base queries.
 */

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { brainSettingsApi } from '@/features/routing/api/brainSettingsApi';
import { Database } from 'lucide-react';

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

interface BrainSettings {
  rag_config: RAGConfigData;
}

interface RagConfigPanelProps {
  brainSettings: BrainSettings | undefined;
  isSaving: boolean;
  onSaveComplete: () => void;
  onSavingChange: (saving: boolean) => void;
}

export function RagConfigPanel({
  brainSettings,
  isSaving,
  onSaveComplete,
  onSavingChange,
}: RagConfigPanelProps) {
  const toast = (message: { title: string; description?: string }) => {
    console.log(`[INFO] ${message.title}: ${message.description}`);
  };

  const handleSaveRAGConfig = async (updates: Partial<RAGConfigData>) => {
    onSavingChange(true);
    try {
      await brainSettingsApi.updateRAGConfig(updates);
      onSaveComplete();
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
      onSavingChange(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          RAG Configuration
        </CardTitle>
        <CardDescription>
          Configure retrieval-augmented generation settings for knowledge base queries.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable RAG */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label htmlFor="rag-enabled" className="text-base">
              Enable RAG
            </Label>
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
                onChange={(e) =>
                  handleSaveRAGConfig({
                    chunk_size: parseInt(e.target.value, 10),
                  })
                }
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
                onChange={(e) =>
                  handleSaveRAGConfig({
                    chunk_overlap: parseInt(e.target.value, 10),
                  })
                }
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
                onChange={(e) =>
                  handleSaveRAGConfig({
                    max_chunks: parseInt(e.target.value, 10),
                  })
                }
              />
              <p className="text-xs text-muted-foreground">
                Maximum chunks to retrieve
              </p>
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
                onChange={(e) =>
                  handleSaveRAGConfig({
                    score_threshold: parseFloat(e.target.value),
                  })
                }
              />
              <p className="text-xs text-muted-foreground">
                Minimum relevance score (0-1)
              </p>
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
              onChange={(e) =>
                handleSaveRAGConfig({
                  hybrid_search_weight: parseFloat(e.target.value),
                })
              }
            />
            <span className="whitespace-nowrap text-sm text-muted-foreground">
              Vector:{' '}
              {Math.round(
                (brainSettings?.rag_config.hybrid_search_weight ?? 0.7) * 100
              )}
              % / BM25:{' '}
              {Math.round(
                (1 - (brainSettings?.rag_config.hybrid_search_weight ?? 0.7)) * 100
              )}
              %
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
            onChange={(e) =>
              handleSaveRAGConfig({
                context_token_limit: parseInt(e.target.value, 10),
              })
            }
          />
          <p className="text-xs text-muted-foreground">
            Maximum tokens for retrieved context (default: 4000)
          </p>
        </div>

        {/* Include Sources */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label htmlFor="include-sources" className="text-base">
              Include Source Citations
            </Label>
            <p className="text-sm text-muted-foreground">
              Add source references to retrieved context
            </p>
          </div>
          <Switch
            id="include-sources"
            checked={brainSettings?.rag_config.include_sources ?? true}
            onCheckedChange={(checked) =>
              handleSaveRAGConfig({ include_sources: checked })
            }
          />
        </div>
      </CardContent>
    </Card>
  );
}
