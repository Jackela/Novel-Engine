/**
 * ApiKeyPanel - API key management for LLM providers
 *
 * BRAIN-033: Brain Settings UI
 *
 * Manages API keys for OpenAI, Anthropic, Gemini, and Ollama configuration.
 */

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { brainSettingsApi } from '@/features/routing/api/brainSettingsApi';
import { CheckCircle2, Database, Eye, EyeOff, Key, XCircle } from 'lucide-react';

interface BrainSettings {
  api_keys: {
    has_openai: boolean;
    has_anthropic: boolean;
    has_gemini: boolean;
    openai_key: string;
    anthropic_key: string;
    gemini_key: string;
  };
  knowledge_base: {
    total_entries: number;
    characters_count: number;
    lore_count: number;
    scenes_count: number;
    is_healthy: boolean;
  };
}

interface ApiKeyPanelProps {
  brainSettings: BrainSettings | undefined;
  brainSettingsLoading: boolean;
  isSaving: boolean;
  onSaveComplete: () => void;
  onSavingChange: (saving: boolean) => void;
}

export function ApiKeyPanel({
  brainSettings,
  brainSettingsLoading,
  isSaving,
  onSaveComplete,
  onSavingChange,
}: ApiKeyPanelProps) {
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [localKeys, setLocalKeys] = useState<Record<string, string>>({
    openai: '',
    anthropic: '',
    gemini: '',
  });
  const [localOllamaUrl, setLocalOllamaUrl] = useState('http://localhost:11434');

  const toast = (message: { title: string; description?: string }) => {
    console.log(`[INFO] ${message.title}: ${message.description}`);
  };

  const handleSaveAPIKey = async (provider: string, key: string) => {
    onSavingChange(true);
    try {
      await brainSettingsApi.updateAPIKeys({ [`${provider}_key`]: key || null });
      onSaveComplete();
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
      onSavingChange(false);
    }
  };

  const handleSaveOllamaUrl = async (url: string) => {
    onSavingChange(true);
    try {
      await brainSettingsApi.updateAPIKeys({ ollama_base_url: url });
      onSaveComplete();
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
      onSavingChange(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5" />
          API Keys
        </CardTitle>
        <CardDescription>
          Configure API keys for LLM providers. Keys are encrypted and stored securely.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Knowledge Base Status */}
        <div className="rounded-lg border bg-muted/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 font-semibold">
            <Database className="h-4 w-4" />
            Knowledge Base Status
          </h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <div>
              <div className="text-2xl font-bold">
                {brainSettingsLoading
                  ? '...'
                  : (brainSettings?.knowledge_base.total_entries ?? 0)}
              </div>
              <div className="text-xs text-muted-foreground">Total Entries</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {brainSettingsLoading
                  ? '...'
                  : (brainSettings?.knowledge_base.characters_count ?? 0)}
              </div>
              <div className="text-xs text-muted-foreground">Characters</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {brainSettingsLoading
                  ? '...'
                  : (brainSettings?.knowledge_base.lore_count ?? 0)}
              </div>
              <div className="text-xs text-muted-foreground">Lore</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {brainSettingsLoading
                  ? '...'
                  : (brainSettings?.knowledge_base.scenes_count ?? 0)}
              </div>
              <div className="text-xs text-muted-foreground">Scenes</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {brainSettings?.knowledge_base.is_healthy ? (
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                ) : (
                  <XCircle className="h-6 w-6 text-red-500" />
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
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            )}
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                id="openai-key"
                type={visibleKeys.openai ? 'text' : 'password'}
                placeholder={
                  brainSettings?.api_keys.has_openai
                    ? brainSettings.api_keys.openai_key
                    : 'sk-...'
                }
                value={localKeys.openai || ''}
                onChange={(e) =>
                  setLocalKeys({ ...localKeys, openai: e.target.value || '' })
                }
                className="pr-20"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 h-7 -translate-y-1/2 px-2"
                onClick={() =>
                  setVisibleKeys({ ...visibleKeys, openai: !visibleKeys.openai })
                }
              >
                {visibleKeys.openai ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
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
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            )}
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                id="anthropic-key"
                type={visibleKeys.anthropic ? 'text' : 'password'}
                placeholder={
                  brainSettings?.api_keys.has_anthropic
                    ? brainSettings.api_keys.anthropic_key
                    : 'sk-ant-...'
                }
                value={localKeys.anthropic || ''}
                onChange={(e) =>
                  setLocalKeys({ ...localKeys, anthropic: e.target.value || '' })
                }
                className="pr-20"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 h-7 -translate-y-1/2 px-2"
                onClick={() =>
                  setVisibleKeys({
                    ...visibleKeys,
                    anthropic: !visibleKeys.anthropic,
                  })
                }
              >
                {visibleKeys.anthropic ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
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
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            )}
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                id="gemini-key"
                type={visibleKeys.gemini ? 'text' : 'password'}
                placeholder={
                  brainSettings?.api_keys.has_gemini
                    ? brainSettings.api_keys.gemini_key
                    : 'AIza-...'
                }
                value={localKeys.gemini || ''}
                onChange={(e) =>
                  setLocalKeys({ ...localKeys, gemini: e.target.value || '' })
                }
                className="pr-20"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 h-7 -translate-y-1/2 px-2"
                onClick={() =>
                  setVisibleKeys({ ...visibleKeys, gemini: !visibleKeys.gemini })
                }
              >
                {visibleKeys.gemini ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
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
            For local models using Ollama. Leave default unless running Ollama on a
            different host.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
