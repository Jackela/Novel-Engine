/**
 * Smart Tags Editor Component
 *
 * BRAIN-038-05: Manual Tag Override
 * UI for editing smart tags on lore entries and scenes
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { X, Plus, Tag as TagIcon, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { smartTagsApi, SmartTagsResponse } from '@/features/routing/api/smartTagsApi';
import { toast } from 'sonner';

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
  const [smartTags, setSmartTags] = useState<SmartTagsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('genre');
  const [newTag, setNewTag] = useState('');

  useEffect(() => {
    loadSmartTags();
  }, [entityType, entityId, storyId, chapterId]);

  async function loadSmartTags() {
    try {
      setLoading(true);
      let response: SmartTagsResponse;
      if (entityType === 'lore') {
        response = await smartTagsApi.getLoreSmartTags(entityId);
      } else if (entityType === 'scene' && storyId && chapterId) {
        response = await smartTagsApi.getSceneSmartTags(storyId, chapterId, entityId);
      } else {
        throw new Error('Invalid entity type or missing required IDs');
      }
      setSmartTags(response);
    } catch (error) {
      console.error('Failed to load smart tags:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to load smart tags');
    } finally {
      setLoading(false);
    }
  }

  async function addManualTag(category: string, tag: string) {
    if (!tag.trim()) return;

    const normalizedTag = tag.trim().toLowerCase();
    const existingManual = smartTags?.manual_smart_tags[category] || [];
    const existingAuto = smartTags?.smart_tags[category] || [];

    if (existingManual.includes(normalizedTag) || existingAuto.includes(normalizedTag)) {
      setNewTag('');
      return;
    }

    try {
      let response: SmartTagsResponse;
      const updatedTags = [...existingManual, normalizedTag];

      if (entityType === 'lore') {
        response = await smartTagsApi.updateLoreManualSmartTags(entityId, {
          category,
          tags: updatedTags,
          replace: true,
        });
      } else if (entityType === 'scene' && storyId && chapterId) {
        response = await smartTagsApi.updateSceneManualSmartTags(
          storyId,
          chapterId,
          entityId,
          {
            category,
            tags: updatedTags,
            replace: true,
          }
        );
      } else {
        throw new Error('Invalid entity type');
      }

      setSmartTags(response);
      setNewTag('');
      toast.success(`Tag "${normalizedTag}" added to ${category}`);
    } catch (error) {
      console.error('Failed to add tag:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to add tag');
    }
  }

  async function removeManualTag(category: string, tag: string) {
    const existingManual = smartTags?.manual_smart_tags[category] || [];
    const updatedTags = existingManual.filter((t) => t !== tag);

    try {
      let response: SmartTagsResponse;

      if (entityType === 'lore') {
        response = await smartTagsApi.updateLoreManualSmartTags(entityId, {
          category,
          tags: updatedTags,
          replace: true,
        });
      } else if (entityType === 'scene' && storyId && chapterId) {
        response = await smartTagsApi.updateSceneManualSmartTags(
          storyId,
          chapterId,
          entityId,
          {
            category,
            tags: updatedTags,
            replace: true,
          }
        );
      } else {
        throw new Error('Invalid entity type');
      }

      setSmartTags(response);
      toast.success(`Tag "${tag}" removed from ${category}`);
    } catch (error) {
      console.error('Failed to remove tag:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to remove tag');
    }
  }

  async function clearCategoryTags(category: string) {
    try {
      let response: SmartTagsResponse;

      if (entityType === 'lore') {
        response = await smartTagsApi.updateLoreManualSmartTags(entityId, {
          category,
          tags: [],
          replace: true,
        });
      } else if (entityType === 'scene' && storyId && chapterId) {
        response = await smartTagsApi.updateSceneManualSmartTags(
          storyId,
          chapterId,
          entityId,
          {
            category,
            tags: [],
            replace: true,
          }
        );
      } else {
        throw new Error('Invalid entity type');
      }

      setSmartTags(response);
      toast.success(`Cleared all manual tags from ${category}`);
    } catch (error) {
      console.error('Failed to clear tags:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to clear tags');
    }
  }

  const categoryInfo = TAG_CATEGORIES.find((c) => c.value === selectedCategory) || TAG_CATEGORIES[0];
  const effectiveTags = smartTags?.effective_tags[selectedCategory] || [];
  const manualTags = smartTags?.manual_smart_tags[selectedCategory] || [];
  const autoTags = (smartTags?.smart_tags[selectedCategory] || []).filter(
    (tag) => !manualTags.includes(tag)
  );

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <div className="text-muted-foreground">Loading smart tags...</div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Category selector tabs */}
      <div className="flex flex-wrap gap-2">
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
          className="flex-1"
        />
        <Button
          type="button"
          size="icon"
          onClick={() => newTag.trim() && addManualTag(selectedCategory, newTag)}
          disabled={!newTag.trim()}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Tags display */}
      <ScrollArea className="h-64 rounded-md border">
        <div className="p-4 space-y-4">
          {/* Manual tags section */}
          {manualTags.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Lock className="h-3 w-3" />
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
                      className="ml-1 hover:bg-white/50 rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
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
                <TagIcon className="h-3 w-3" />
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

          {/* Empty state */}
          {effectiveTags.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              <TagIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
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
          className="w-full"
        >
          Clear All Manual Tags from {categoryInfo.label}
        </Button>
      )}
    </div>
  );
}
