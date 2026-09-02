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
export function* iterateResidentContextSections(view: ResidentContextView): Generator<string> {
  if (view.outline !== null) {
    yield "";
    yield "OUTLINE (the writer's recorded plan):";
    yield PROJECT_OUTLINE_BEGIN;
    yield sanitizeResidentProse(view.outline.markdown);
    if (view.outline.linkedBeat !== null) {
      yield `Current beat: "${sanitizeResidentProse(view.outline.linkedBeat.title)}" — this chapter fulfills this outline section.`;
    }
    yield PROJECT_OUTLINE_END;
  }
  if (view.priorStory.length > 0) {
    yield "";
    yield "PRIOR STORY (rolling summary of every earlier chapter, in reading order):";
    yield PRIOR_STORY_BEGIN;
    for (const entry of view.priorStory) {
      yield `${entry.ordinal}. ${sanitizeResidentProse(entry.title)} — ${sanitizeResidentProse(entry.digest)}`;
    }
    yield PRIOR_STORY_END;
  }
  if (view.recentText !== null) {
    yield "";
    yield "RECENT TEXT (closing passage of the most recent earlier chapter):";
    yield RECENT_TEXT_BEGIN;
    yield sanitizeResidentProse(view.recentText);
    yield RECENT_TEXT_END;
  }
}

/** Compatibility materializer for callers that own an array-shaped boundary. */
export function renderResidentContextSections(view: ResidentContextView): string[] {
  return [...iterateResidentContextSections(view)];
}
