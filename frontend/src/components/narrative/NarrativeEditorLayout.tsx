/**
 * NarrativeEditorLayout - Main layout component for the narrative writing interface.
 *
 * Why: Combines the NarrativeSidebar (20% width) and EditorComponent (80% width)
 * into a cohesive writing environment, following the PRD layout specifications.
 */
import { useState } from 'react';

import { cn } from '@/lib/utils';
import { NarrativeSidebar, MOCK_CHAPTERS } from './NarrativeSidebar';
import { EditorComponent } from './EditorComponent';
import type { OutlinerChapter } from './NarrativeSidebar';

interface NarrativeEditorLayoutProps {
  /** Story chapters data (optional, defaults to mock data for development) */
  chapters?: OutlinerChapter[];
  /** Additional CSS classes for the container */
  className?: string;
}

/**
 * NarrativeEditorLayout - The main writing interface layout.
 *
 * Why: Provides a standard split-pane layout common in professional writing
 * applications (Scrivener, Ulysses), with the outline on the left for
 * navigation and the editor on the right for content creation.
 */
export function NarrativeEditorLayout({
  chapters = MOCK_CHAPTERS,
  className,
}: NarrativeEditorLayoutProps) {
  // Track active scene for sidebar highlighting and content loading
  const [activeSceneId, setActiveSceneId] = useState<string | undefined>(
    chapters[0]?.scenes[0]?.id
  );

  // Find the active scene's content (placeholder for now)
  const getSceneContent = (sceneId: string | undefined): string => {
    if (!sceneId) {
      return '<p>Select a scene from the outline to start writing...</p>';
    }
    // Find the scene in the chapters
    for (const chapter of chapters) {
      const scene = chapter.scenes.find((s) => s.id === sceneId);
      if (scene) {
        return `<h2>${scene.title}</h2><p>Start writing your scene content here...</p>`;
      }
    }
    return '<p>Scene not found</p>';
  };

  const handleSceneSelect = (sceneId: string, _chapterId: string) => {
    setActiveSceneId(sceneId);
  };

  const handleEditorChange = (html: string) => {
    // Future: Save content to backend via API
    console.log('Editor content changed:', html.substring(0, 100) + '...');
  };

  return (
    <div
      className={cn('flex h-full w-full overflow-hidden', className)}
      data-testid="narrative-editor-layout"
    >
      {/* Sidebar - 20% width */}
      <div className="w-1/5 min-w-[200px] max-w-[300px] shrink-0">
        <NarrativeSidebar
          chapters={chapters}
          activeSceneId={activeSceneId}
          onSceneSelect={handleSceneSelect}
          className="h-full"
        />
      </div>

      {/* Editor - 80% width (remaining space) */}
      <main className="flex flex-1 flex-col overflow-hidden bg-background p-4">
        <EditorComponent
          initialContent={getSceneContent(activeSceneId)}
          onChange={handleEditorChange}
          className="h-full"
        />
      </main>
    </div>
  );
}

export default NarrativeEditorLayout;
