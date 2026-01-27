/**
 * StoryList - List display of stories
 */
import { useState } from 'react';
import { Filter, Sparkles } from 'lucide-react';
import { Button, Input } from '@/shared/components/ui';
import { LoadingSpinner, EmptyState } from '@/shared/components/feedback';
import { StoryCard } from './StoryCard';
import type { Story, StoryMood } from '@/shared/types/story';

interface StoryListProps {
  stories: Story[];
  isLoading?: boolean;
  onGenerate?: (() => void) | undefined;
  onSelect?: ((story: Story) => void) | undefined;
  onDelete?: ((id: string) => void) | undefined;
  onExport?: ((id: string) => void) | undefined;
}

const moodFilters: { value: StoryMood | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'dramatic', label: 'Dramatic' },
  { value: 'action', label: 'Action' },
  { value: 'mysterious', label: 'Mysterious' },
  { value: 'emotional', label: 'Emotional' },
  { value: 'tense', label: 'Tense' },
  { value: 'calm', label: 'Calm' },
];

export function StoryList({
  stories,
  isLoading = false,
  onGenerate,
  onSelect,
  onDelete,
  onExport,
}: StoryListProps) {
  const [moodFilter, setMoodFilter] = useState<StoryMood | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredStories = stories.filter((story) => {
    const matchesMood = moodFilter === 'all' || story.mood === moodFilter;
    const matchesSearch =
      searchQuery === '' ||
      story.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      story.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesMood && matchesSearch;
  });

  if (isLoading) {
    return <LoadingSpinner fullScreen text="Loading stories..." />;
  }

  return (
    <div className="space-y-4">
      <StoryListControls
        moodFilter={moodFilter}
        onMoodFilterChange={setMoodFilter}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        onGenerate={onGenerate}
      />

      {/* List or Empty State */}
      {filteredStories.length === 0 ? (
        <EmptyState
          title={stories.length === 0 ? 'No stories yet' : 'No matching stories'}
          description={
            stories.length === 0
              ? 'Generate your first story to begin your narrative journey'
              : 'Try adjusting your filters or search query'
          }
          {...(stories.length === 0 && onGenerate
            ? { action: { label: 'Generate Story', onClick: onGenerate } }
            : {})}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredStories.map((story) => (
            <StoryCard
              key={story.id}
              story={story}
              {...(onSelect ? { onSelect } : {})}
              {...(onDelete ? { onDelete } : {})}
              {...(onExport ? { onExport } : {})}
            />
          ))}
        </div>
      )}
    </div>
  );
}

type StoryListControlsProps = {
  moodFilter: StoryMood | 'all';
  onMoodFilterChange: (value: StoryMood | 'all') => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onGenerate?: (() => void) | undefined;
};

function StoryListControls({
  moodFilter,
  onMoodFilterChange,
  searchQuery,
  onSearchQueryChange,
  onGenerate,
}: StoryListControlsProps) {
  return (
    <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <div className="flex flex-wrap gap-1">
          {moodFilters.map((filter) => (
            <Button
              key={filter.value}
              variant={moodFilter === filter.value ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onMoodFilterChange(filter.value)}
            >
              {filter.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex w-full items-center gap-2 sm:w-auto">
        <Input
          placeholder="Search stories..."
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
          className="w-full sm:w-64"
        />
        {onGenerate && (
          <Button onClick={onGenerate}>
            <Sparkles className="mr-2 h-4 w-4" />
            Generate
          </Button>
        )}
      </div>
    </div>
  );
}
