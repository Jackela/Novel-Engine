import type { ResidentContextView } from "./resident_context.js";
import {
  PRIOR_STORY_BEGIN,
  PRIOR_STORY_END,
  PROJECT_OUTLINE_BEGIN,
  PROJECT_OUTLINE_END,
  RECENT_TEXT_BEGIN,
  RECENT_TEXT_END,
  sanitizeResidentProse,
} from "./sanitization.js";

/**
 * The searchable text of the assembled resident view (#315): outline, beat,
 * every prior title/digest, and the recent tail. Keys match over this RAW
 * view text — render-time sanitization alters markers, not word content, so
 * hits are identical and matching stays independent of rendering.
 */
export function residentMatchCorpus(view: ResidentContextView): string {
  const parts: string[] = [];
  if (view.outline !== null) {
    parts.push(view.outline.markdown);
    if (view.outline.linkedBeat !== null) {
      parts.push(view.outline.linkedBeat.title, view.outline.linkedBeat.content);
    }
  }
  for (const prior of view.priorStory) {
    parts.push(prior.title, prior.digest);
  }
  if (view.recentText !== null) {
    parts.push(view.recentText);
  }
  return parts.join("\n");
}

/**
 * Render the resident sections in prompt order. Derived prose crosses through
 * sanitizeResidentProse so no project-derived value can forge a bracketed
 * marker. The linked beat stays inside the outline's reference-data block.
 */
export function renderResidentContextSections(view: ResidentContextView): string[] {
  const sections: string[] = [];
  if (view.outline !== null) {
    sections.push(
      "",
      "OUTLINE (the writer's recorded plan):",
      PROJECT_OUTLINE_BEGIN,
      sanitizeResidentProse(view.outline.markdown),
    );
    if (view.outline.linkedBeat !== null) {
      sections.push(
        `Current beat: "${sanitizeResidentProse(view.outline.linkedBeat.title)}" — this chapter fulfills this outline section.`,
      );
    }
    sections.push(PROJECT_OUTLINE_END);
  }
  if (view.priorStory.length > 0) {
    sections.push(
      "",
      "PRIOR STORY (rolling summary of every earlier chapter, in reading order):",
      PRIOR_STORY_BEGIN,
      ...view.priorStory.map(
        (entry) =>
          `${entry.ordinal}. ${sanitizeResidentProse(entry.title)} — ${sanitizeResidentProse(entry.digest)}`,
      ),
      PRIOR_STORY_END,
    );
  }
  if (view.recentText !== null) {
    sections.push(
      "",
      "RECENT TEXT (closing passage of the most recent earlier chapter):",
      RECENT_TEXT_BEGIN,
      sanitizeResidentProse(view.recentText),
      RECENT_TEXT_END,
    );
  }
  return sections;
}
