/**
 * Smart Tags Editor Component
 *
 * BRAIN-038-05: Manual Tag Override
 * UI for editing smart tags on lore entries and scenes
 *
 * OPT-011: Refactored to use React Query with optimistic updates
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { X, Plus, Tag as TagIcon, Lock, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useLoreSmartTags,
  useSceneSmartTags,
  useAddLoreTag,
  useAddSceneTag,
  useRemoveLoreTag,
  useRemoveSceneTag,
  useClearLoreCategoryTags,
  useClearSceneCategoryTags,
} from '@/features/routing/api/smartTagsHooks';

interface SmartTagsEditorProps {
  /** Type of entity being edited */
  entityType: 'lore' | 'scene';
  /** Entity ID */
  entityId: string;
  /** Additional IDs for scene entities */
  storyId?: string;
  chapterId?: string;
  /** Class name for styling */
  className?: string;
}

const TAG_CATEGORIES = [
  { value: 'genre', label: 'Genre', color: 'bg-blue-100 text-blue-800 border-blue-200' },
  { value: 'mood', label: 'Mood', color: 'bg-purple-100 text-purple-800 border-purple-200' },
  { value: 'themes', label: 'Themes', color: 'bg-green-100 text-green-800 border-green-200' },
  { value: 'characters_present', label: 'Characters', color: 'bg-orange-100 text-orange-800 border-orange-200' },
  { value: 'locations', label: 'Locations', color: 'bg-teal-100 text-teal-800 border-teal-200' },
];

export function SmartTagsEditor({
  entityType,
  entityId,
  storyId,
  chapterId,
  className,
}: SmartTagsEditorProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('genre');
  const [newTag, setNewTag] = useState('');

  // React Query hooks for data fetching
  const {
    data: smartTags,
    isLoading,
    error,
  } = entityType === 'lore'
    ? useLoreSmartTags(entityId)
    : useSceneSmartTags(storyId ?? '', chapterId ?? '', entityId);

  // React Query hooks for mutations with optimistic updates
  const addTagMutation =
    entityType === 'lore'
      ? useAddLoreTag(entityId)
      : useAddSceneTag(storyId ?? '', chapterId ?? '', entityId);

  const removeTagMutation =
    entityType === 'lore'
      ? useRemoveLoreTag(entityId)
      : useRemoveSceneTag(storyId ?? '', chapterId ?? '', entityId);

  const clearCategoryMutation =
    entityType === 'lore'
      ? useClearLoreCategoryTags(entityId)
      : useClearSceneCategoryTags(storyId ?? '', chapterId ?? '', entityId);

  // Check if any mutation is pending
  const isMutating =
    addTagMutation.isPending || removeTagMutation.isPending || clearCategoryMutation.isPending;

  function addManualTag(category: string, tag: string) {
    if (!tag.trim()) return;

    const normalizedTag = tag.trim().toLowerCase();
    const existingManual = smartTags?.manual_smart_tags[category] || [];
    const existingAuto = smartTags?.smart_tags[category] || [];

    if (existingManual.includes(normalizedTag) || existingAuto.includes(normalizedTag)) {
      setNewTag('');
      return;
    }

    addTagMutation.mutate({ category, tag: normalizedTag });
    setNewTag('');
  }

  function removeManualTag(category: string, tag: string) {
    removeTagMutation.mutate({ category, tag });
  }

  function clearCategoryTags(category: string) {
    clearCategoryMutation.mutate(category);
  }

  const categoryInfo = TAG_CATEGORIES.find((c) => c.value === selectedCategory) ?? TAG_CATEGORIES[0]!;
  const effectiveTags = smartTags?.effective_tags[selectedCategory] || [];
  const manualTags = smartTags?.manual_smart_tags[selectedCategory] || [];
  const autoTags = (smartTags?.smart_tags[selectedCategory] || []).filter(
    (tag) => !manualTags.includes(tag)
  );

  // === Loading State ===
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading smart tags...</span>
        </div>
      </div>
    );
  }

  // === Error State ===
  if (error) {
    return (
      <div className={cn('rounded-lg border border-destructive/50 bg-destructive/10 p-4', className)}>
        <div className="flex items-center gap-2 text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm">
            {error instanceof Error ? error.message : 'Failed to load smart tags'}
          </span>
        </div>
      </div>
    );
  }

  // === Empty State (no data at all) ===
  if (!smartTags) {
    return (
      <div className={cn('rounded-lg border border-dashed p-8 text-center', className)}>
        <TagIcon className="mx-auto h-8 w-8 text-muted-foreground/50" />
        <p className="mt-2 text-sm text-muted-foreground">No smart tags data available</p>
      </div>
    );
  }

  // === Ready State ===
  return (
    <div className={cn('flex flex-col gap-4', className)} aria-busy={isMutating}>
      {/* Category selector tabs */}
      <div className="flex flex-wrap gap-2" role="tablist">
        {TAG_CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setSelectedCategory(cat.value)}
            className={cn(
              'px-4 py-2 rounded-md text-sm font-medium transition-colors',
              selectedCategory === cat.value
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            )}
            role="tab"
            aria-selected={selectedCategory === cat.value}
            aria-controls={`${cat.value}-panel`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Add new tag input */}
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder={`Add tag to ${categoryInfo.label.toLowerCase()}...`}
          value={newTag}
          onChange={(e) => setNewTag(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && newTag.trim()) {
              addManualTag(selectedCategory, newTag);
            }
          }}
          disabled={addTagMutation.isPending}
          className="flex-1"
          aria-describedby="add-tag-hint"
        />
        <span id="add-tag-hint" className="sr-only">
          Press Enter to add the tag
        </span>
        <Button
          type="button"
          size="icon"
          onClick={() => newTag.trim() && addManualTag(selectedCategory, newTag)}
          disabled={!newTag.trim() || addTagMutation.isPending}
          aria-label={`Add tag to ${categoryInfo.label}`}
        >
          {addTagMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Tags display */}
      <ScrollArea className="h-64 rounded-md border">
        <div
          className="p-4 space-y-4"
          id={`${selectedCategory}-panel`}
          role="tabpanel"
        >
          {/* Manual tags section */}
          {manualTags.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Lock className="h-3 w-3" aria-hidden="true" />
                Manual Tags (never overridden)
              </div>
              <div className="flex flex-wrap gap-2">
                {manualTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className={cn('gap-1 px-3 py-1', categoryInfo.color)}
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeManualTag(selectedCategory, tag)}
                      disabled={removeTagMutation.isPending}
                      className="ml-1 hover:bg-white/50 rounded-full p-0.5 disabled:opacity-50"
                      aria-label={`Remove tag ${tag}`}
                    >
                      {removeTagMutation.isPending &&
                      removeTagMutation.variables?.tag === tag ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <X className="h-3 w-3" />
                      )}
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Auto-generated tags section */}
          {autoTags.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <TagIcon className="h-3 w-3" aria-hidden="true" />
                Auto-Generated Tags
              </div>
              <div className="flex flex-wrap gap-2">
                {autoTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="outline"
                    className="px-3 py-1 opacity-70"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Empty state (no tags for this category) */}
          {effectiveTags.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              <TagIcon className="h-8 w-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p>No tags for {categoryInfo.label.toLowerCase()} yet.</p>
              <p className="text-sm">Add a manual tag above to get started.</p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Clear all manual tags button */}
      {manualTags.length > 0 && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => clearCategoryTags(selectedCategory)}
          disabled={clearCategoryMutation.isPending}
          className="w-full"
        >
          {clearCategoryMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Clearing...
            </>
          ) : (
            <>Clear All Manual Tags from {categoryInfo.label}</>
          )}
        </Button>
      )}
    </div>
  );
}
