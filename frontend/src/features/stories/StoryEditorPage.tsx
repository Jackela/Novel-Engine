/**
 * StoryEditorPage - Full-page story editor with streaming generation
 */
import { useCallback, useState } from 'react';
import { NarrativeEditor } from './components/NarrativeEditor';
import type { WorldContext } from './hooks/useStoryStream';

export default function StoryEditorPage() {
  const [lastContent, setLastContent] = useState('');

  // In a real implementation, this would come from:
  // 1. URL params (story ID to load)
  // 2. Weaver store (selected characters/locations)
  // 3. API call to fetch story state
  const worldContext: WorldContext = {
    characters: [
      {
        id: 'elena',
        name: 'Elena',
        type: 'character',
        description: 'A young scholar seeking ancient knowledge',
      },
      {
        id: 'marcus',
        name: 'Marcus',
        type: 'character',
        description: 'A wandering knight with a mysterious past',
      },
    ],
    locations: [
      {
        id: 'library',
        name: 'The Great Library',
        type: 'location',
        description: 'An ancient repository of forbidden knowledge',
      },
    ],
    entities: [
      {
        id: 'tome',
        name: 'The Crimson Tome',
        type: 'item',
        description: 'A book that whispers secrets',
      },
    ],
    current_scene: 'The Discovery',
    narrative_style: 'dark fantasy',
  };

  const handleContentChange = useCallback((content: string) => {
    setLastContent(content);
  }, []);

  const handleComplete = useCallback(() => {
    // Future: trigger auto-save or analytics here
    void lastContent.length;
  }, [lastContent.length]);

  return (
    <div className="container mx-auto max-w-4xl p-6">
      <NarrativeEditor
        worldContext={worldContext}
        onContentChange={handleContentChange}
        onComplete={handleComplete}
      />
    </div>
  );
}
