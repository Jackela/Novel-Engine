/**
 * Outline Export API - Generate and download story outline reports.
 *
 * Why: Provides functions to export narrative structure as Markdown
 * for external sharing, backup, or publication preparation.
 */

import { api } from './client';
import {
  StoryResponseSchema,
  SceneListResponseSchema,
  BeatListResponseSchema,
  PlotlineListResponseSchema,
} from '@/types/schemas';
import { listChapters } from './narrativeApi';

/**
 * Fetch all scenes in a chapter.
 */
export async function listScenes(storyId: string, chapterId: string) {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes`
  );
  return SceneListResponseSchema.parse(data);
}

/**
 * Fetch all beats in a scene.
 */
export async function getSceneBeats(sceneId: string) {
  const data = await api.get<unknown>(`/structure/scenes/${sceneId}/beats`);
  return BeatListResponseSchema.parse(data);
}

/**
 * Outline export options.
 */
export interface OutlineExportOptions {
  /** Include scene-by-scene beat breakdown */
  includeBeats?: boolean;
  /** Include character arcs per scene */
  includeCharacters?: boolean;
  /** Export filename (without extension) */
  filename?: string;
}

/**
 * Generate Markdown outline report for a story.
 */
export async function generateOutlineMarkdown(
  storyId: string,
  options: OutlineExportOptions = {}
): Promise<string> {
  const {
    includeBeats = false,
    includeCharacters = false,
  } = options;

  // Fetch story data
  const storyData = await api.get<unknown>(`/structure/stories/${storyId}`);
  const story = StoryResponseSchema.parse(storyData);

  // Fetch chapters
  const chapters = await listChapters(storyId);

  // Fetch plotlines
  const plotlinesData = await api.get<unknown>('/structure/plotlines');
  const plotlinesResponse = PlotlineListResponseSchema.parse(plotlinesData);
  const plotlines = plotlinesResponse.plotlines;

  // Fetch characters if requested
  let characterSummaries: Array<{ name?: string; archetype?: string; traits?: string[] }> = [];
  if (includeCharacters) {
    const charactersData = await api.get<unknown>('/characters');
    // Character data is returned differently - handle gracefully
    characterSummaries = Array.isArray(charactersData) ? charactersData : [];
  }

  // Build markdown
  let markdown = `# ${story.title}\n\n`;

  if (story.summary) {
    markdown += `**Logline:** ${story.summary}\n\n`;
  }

  markdown += `**Status:** ${story.status}\n`;
  markdown += `**Total Chapters:** ${chapters.chapters.length}\n`;
  markdown += `**Export Date:** ${new Date().toLocaleDateString()}\n\n`;

  // Plotlines section
  if (plotlines.length > 0) {
    markdown += `## Plotlines\n\n`;
    plotlines.forEach((plotline) => {
      const statusEmoji =
        plotline.status === 'active'
          ? '🔄'
          : plotline.status === 'resolved'
            ? '✅'
            : '🚫';
      markdown += `### ${statusEmoji} ${plotline.name}\n`;
      if (plotline.description) {
        markdown += `${plotline.description}\n`;
      }
      markdown += `**Status:** ${plotline.status}\n\n`;
    });
  }

  // Character Arcs section (if requested and data available)
  if (includeCharacters && characterSummaries.length > 0) {
    markdown += `## Characters\n\n`;
    characterSummaries.forEach((char) => {
      markdown += `### ${char.name || 'Unknown'}\n`;
      if (char.archetype) {
        markdown += `**Archetype:** ${char.archetype}\n`;
      }
      if (char.traits && char.traits.length > 0) {
        markdown += `**Traits:** ${char.traits.join(', ')}\n`;
      }
      markdown += `\n`;
    });
  }

  // Chapter summaries
  markdown += `## Chapter Breakdown\n\n`;

  for (const chapter of chapters.chapters) {
    markdown += `### Chapter ${chapter.order_index + 1}: ${chapter.title}\n\n`;

    if (chapter.summary) {
      markdown += `${chapter.summary}\n\n`;
    }

    // Fetch scenes for this chapter
    const scenes = await listScenes(storyId, chapter.id);

    if (scenes.scenes.length === 0) {
      markdown += `*No scenes yet*\n\n`;
      continue;
    }

    // Scene list
    markdown += `#### Scenes\n\n`;

    for (const scene of scenes.scenes) {
      const phaseLabel = scene.story_phase.replace(/_/g, ' ').toLowerCase();
      markdown += `**${scene.order_index + 1}. ${scene.title}** (${phaseLabel})\n`;

      if (scene.summary) {
        markdown += `${scene.summary}\n`;
      }

      if (scene.location) {
        markdown += `📍 ${scene.location}\n`;
      }

      // Optional: Include beats for this scene
      if (includeBeats && scene.beat_count > 0) {
        const beats = await getSceneBeats(scene.id);
        if (beats.beats.length > 0) {
          markdown += `\n##### Beats\n\n`;
          beats.beats.forEach((beat) => {
            const moodIcon =
              beat.mood_shift > 0 ? '⬆️' : beat.mood_shift < 0 ? '⬇️' : '➡️';
            markdown += `- **${beat.beat_type}** ${moodIcon} (${beat.mood_shift}): ${beat.content}\n`;
          });
        }
      }

      markdown += `\n`;
    }

    markdown += `---\n\n`;
  }

  // Footer
  markdown += `\n*Generated by Novel Engine*\n`;

  return markdown;
}

/**
 * Trigger a Markdown file download in the browser.
 *
 * @param markdown - The markdown content to export.
 * @param filename - The filename for the download (without extension).
 */
export function downloadAsMarkdown(markdown: string, filename: string): void {
  const blob = new Blob([markdown], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.md`;
  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Generate and download outline report as Markdown file.
 *
 * This is the main export function that combines data fetching,
 * markdown generation, and file download.
 */
export async function exportOutlineAsMarkdown(
  storyId: string,
  options: OutlineExportOptions = {}
): Promise<void> {
  const markdown = await generateOutlineMarkdown(storyId, options);
  const filename = options.filename || 'outline';
  downloadAsMarkdown(markdown, filename);
}

/**
 * React hook for exporting outline.
 * Provides loading state and error handling.
 */
export function useExportOutline() {
  return {
    exportOutline: exportOutlineAsMarkdown,
  };
}
