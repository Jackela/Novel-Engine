/**
 * PromptsPage - Prompt Lab list view
 *
 * BRAIN-019A: Prompt Lab - List View
 * Displays all prompt templates with search and filter capabilities.
 */

import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { usePrompts, usePromptTags, useDeletePrompt } from '../api/promptApi';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ErrorState } from '@/shared/components/feedback';
import { EmptyState } from '@/shared/components/feedback';
import {
  Search,
  Plus,
  Filter,
  Trash2,
  Edit,
  Eye,
  Hash,
  Calendar,
  Layers,
} from 'lucide-react';
import type { PromptSummary } from '@/types/schemas';

export function PromptsPage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState<string>('all');
  const [selectedTag, setSelectedTag] = useState<string>('all');

  // Build filters object, only including defined values
  const filters: {
    tags?: string;
    model?: string;
    limit: number;
  } = {
    limit: 100,
  };
  if (selectedTag !== 'all') {
    filters.tags = selectedTag;
  }
  if (selectedModel !== 'all') {
    filters.model = selectedModel;
  }

  const {
    data: promptsData,
    isLoading,
    error,
  } = usePrompts(filters);

  const { data: tagsData } = usePromptTags();
  const deleteMutation = useDeletePrompt();

  // Filter prompts based on search query (client-side for name/description search)
  const filteredPrompts = promptsData?.prompts.filter((prompt) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      prompt.name.toLowerCase().includes(query) ||
      prompt.description.toLowerCase().includes(query)
    );
  }) ?? [];

  // Extract unique model names from prompts
  const modelOptions = [
    'all',
    ...new Set(
      promptsData?.prompts
        .map((p) => p.model_name)
        .filter((m): m is string => Boolean(m)) ?? []
    ),
  ];

  // Extract all unique tags
  const allTags = tagsData
    ? Object.values(tagsData).flat()
    : [];

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete prompt "${name}"?`)) {
      await deleteMutation.mutateAsync(id);
    }
  };

  if (error) {
    return (
      <ErrorState
        title="Failed to load prompts"
        message={error.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PromptsHeader navigate={navigate} />

      {/* Search and Filter Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search prompts by name or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Filters */}
            <div className="flex gap-2">
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="w-[140px]">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Models</SelectItem>
                  {modelOptions.slice(1).map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selectedTag} onValueChange={setSelectedTag}>
                <SelectTrigger className="w-[140px]">
                  <Hash className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Tag" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tags</SelectItem>
                  {allTags.slice(0, 20).map((tag) => (
                    <SelectItem key={tag} value={tag}>
                      {tag}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Prompts Grid */}
      {isLoading ? (
        <LoadingState />
      ) : filteredPrompts.length === 0 ? (
        !searchQuery && selectedModel === 'all' && selectedTag === 'all' ? (
          <EmptyState
            title="No prompts found"
            description="Get started by creating your first prompt template"
            action={{
              label: 'Create Prompt',
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onClick: () => navigate({ to: '/brain/prompts/new' as any }),
            }}
          />
        ) : (
          <EmptyState
            title="No prompts found"
            description="Try adjusting your search or filters"
          />
        )
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPrompts.map((prompt) => (
            <PromptCard
              key={prompt.id}
              prompt={prompt}
              onDelete={() => handleDelete(prompt.id, prompt.name)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onEdit={() => navigate({ to: `/brain/prompts/${prompt.id}` as any })}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onView={() => navigate({ to: `/brain/prompts/${prompt.id}` as any })}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface PromptsHeaderProps {
  navigate: ReturnType<typeof useNavigate>;
}

function PromptsHeader({ navigate }: PromptsHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Prompt Lab</h1>
        <p className="text-muted-foreground">
          Manage and version your AI prompt templates
        </p>
      </div>
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <Button onClick={() => navigate({ to: '/brain/prompts/new' as any })}>
        <Plus className="mr-2 h-4 w-4" />
        New Prompt
      </Button>
    </div>
  );
}

interface PromptCardProps {
  prompt: PromptSummary;
  onDelete: () => void;
  onEdit: () => void;
  onView: () => void;
}

function PromptCard({ prompt, onDelete, onEdit, onView }: PromptCardProps) {
  return (
    <Card className="group hover:shadow-md transition-shadow">
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="truncate text-lg">{prompt.name}</CardTitle>
            {prompt.description && (
              <CardDescription className="line-clamp-2">
                {prompt.description}
              </CardDescription>
            )}
          </div>
          <Badge variant="secondary" className="ml-2 shrink-0">
            v{prompt.version}
          </Badge>
        </div>

        {/* Tags */}
        {prompt.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {prompt.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
            {prompt.tags.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{prompt.tags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {/* Metadata */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            {prompt.model_name && (
              <div className="flex items-center gap-1">
                <Layers className="h-3 w-3" />
                <span className="truncate max-w-[100px]">{prompt.model_name}</span>
              </div>
            )}
            {prompt.variable_count > 0 && (
              <div className="flex items-center gap-1">
                <Hash className="h-3 w-3" />
                <span>{prompt.variable_count} variables</span>
              </div>
            )}
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{new Date(prompt.updated_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button
              variant="ghost"
              size="sm"
              className="flex-1"
              onClick={onView}
            >
              <Eye className="mr-2 h-4 w-4" />
              View
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="flex-1"
              onClick={onEdit}
            >
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <Card key={i} className="animate-pulse">
          <CardHeader className="space-y-2">
            <div className="h-5 bg-muted rounded w-3/4" />
            <div className="h-4 bg-muted rounded w-full" />
            <div className="h-4 bg-muted rounded w-1/2" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="h-8 bg-muted rounded" />
              <div className="h-8 bg-muted rounded w-2/3" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default PromptsPage;
