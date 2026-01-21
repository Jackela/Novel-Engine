/**
 * StoriesPage - Story library page
 */
import { useState } from 'react';
import { useAllStories, useDeleteStory, useExportStory } from './api/storyApi';
import { StoryList } from './components/StoryList';
import { StoryViewer } from './components/StoryViewer';
import { ErrorState } from '@/shared/components/feedback';
import type { Story } from '@/shared/types/story';

export default function StoriesPage() {
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const { data: stories = [], isLoading, error } = useAllStories();
  const deleteMutation = useDeleteStory();
  const exportMutation = useExportStory();

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this story?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleExport = async (id: string, format: 'markdown' | 'pdf' | 'json' = 'markdown') => {
    const blob = await exportMutation.mutateAsync({ id, format });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `story-${id}.${format === 'markdown' ? 'md' : format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <ErrorState
        title="Failed to load stories"
        message={error.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  if (selectedStory) {
    return (
      <StoryViewer
        story={selectedStory}
        onBack={() => setSelectedStory(null)}
        onExport={(format) => handleExport(selectedStory.id, format)}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Story Library</h1>
        <p className="text-muted-foreground">
          Browse and manage your generated narratives
        </p>
      </div>

      {/* Story List */}
      <StoryList
        stories={stories}
        isLoading={isLoading}
        onSelect={setSelectedStory}
        onDelete={handleDelete}
        onExport={(id) => handleExport(id)}
        onGenerate={() => {
          // Navigate to orchestration page for generation
          window.location.href = '/orchestration';
        }}
      />
    </div>
  );
}
