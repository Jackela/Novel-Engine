import { linkedChapterBeat } from "./beat_association_service.js";
import { BoundedPromptWriter } from "./generation_capacity.js";
import { triggeredLoreSections } from "./lore_injection.js";
import type { LoreEntrySource } from "./lorebook.js";
import type { OutlineBeat } from "./outline_beats.js";
import type { DocumentWithCurrent, ProjectScope, StudioStore } from "./ports/studio_store.js";
import { renderResidentContextSections, residentMatchCorpus } from "./resident_context_render.js";
import { formatAuthorInstruction, formatUntrustedManuscript } from "./sanitization.js";

// The rendering half lives in resident_context_render.ts; re-exported here so
// the module's public API (ADR-0004 layer 1 consumers) stays unchanged.
export { renderResidentContextSections, residentMatchCorpus } from "./resident_context_render.js";

/**
 * Resident context (#314, ADR-0004 layer 1): every proposal generation assembles,
 * ahead of the target manuscript, the outline with its current beat position, a
 * rolling summary of EVERY prior chapter in reading order (#312: volume order,
 * then in-volume order; no eliding), and the tail of the most recent earlier
 * chapter. The assembly is pure — inputs are documents plus the target plus the
 * resolved beat link — so coverage is pinned by unit tests rather than by
 * provider behavior.
 */
export const PRIOR_STORY_DIGEST_WORD_LIMIT = 60;
export const PRIOR_STORY_DIGEST_CODE_POINT_LIMIT = 512;
export const RECENT_TEXT_CHARACTER_LIMIT = 1200;
/** How far past the cut a line/space boundary may lie before the cut is hard. */
export const RECENT_TEXT_BOUNDARY_WINDOW = 200;
export const EMPTY_CHAPTER_DIGEST_PLACEHOLDER = "(no text yet)";

/** The minimal chapter facts the assembler needs; store rows satisfy this shape. */
export interface ResidentChapterSource {
  readonly id: string;
  readonly kind: string;
  readonly title: string;
  readonly position: number;
  readonly volumeId: string | null;
  /** The current revision's markdown, or null when the chapter has none. */
  readonly contentMarkdown: string | null;
}

/** Volumes arrive in reading order (the StudioStore contract); index = rank. */
export interface ResidentVolumeSource {
  readonly id: string;
}

export interface ResidentContextSource {
  /** Full markdown of the project's authoritative outline document, else null. */
  readonly outlineMarkdown: string | null;
  /** The target's linked beat, resolved against the live outline (#313). */
  readonly linkedBeat: OutlineBeat | null;
  readonly volumes: readonly ResidentVolumeSource[];
  readonly chapters: readonly ResidentChapterSource[];
  readonly targetDocumentId: string;
}

export interface PriorChapterDigest {
  readonly ordinal: number;
  readonly title: string;
  readonly digest: string;
}

export interface ResidentOutlineContext {
  readonly markdown: string;
  readonly linkedBeat: OutlineBeat | null;
}

export interface ResidentContextView {
  readonly outline: ResidentOutlineContext | null;
  readonly priorStory: PriorChapterDigest[];
  readonly recentText: string | null;
}

/** Flatten chapter markdown into one compact prose line for the rolling summary. */
function flattenProse(markdown: string): string {
  return String(markdown)
    .replace(/\r\n?/g, "\n")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]*)\]\(([^)]*)\)/g, "$1")
    .replace(/^ {0,3}#{1,6} +/gm, "")
    .replace(/\*\*/g, "")
    .replace(/\*/g, "")
    .replace(/`/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Deterministic per-chapter digest: the flattened opening prose of the
 * chapter's own text, truncated to the word budget. Never model-generated.
 */
export function chapterDigest(markdown: string): string {
  const flat = flattenProse(markdown);
  const words = flat === "" ? [] : flat.split(" ");
  const wordTruncated = words.length > PRIOR_STORY_DIGEST_WORD_LIMIT;
  const wordBounded = wordTruncated
    ? words.slice(0, PRIOR_STORY_DIGEST_WORD_LIMIT).join(" ")
    : flat;
  const codePoints = [...wordBounded];
  const codePointTruncated = codePoints.length > PRIOR_STORY_DIGEST_CODE_POINT_LIMIT;
  if (!wordTruncated && !codePointTruncated) return wordBounded;
  return `${codePoints.slice(0, PRIOR_STORY_DIGEST_CODE_POINT_LIMIT - 1).join("")}…`;
}

/**
 * The closing passage of one chapter, trimmed to the character limit at a
 * safe boundary: prefer the next newline inside the snap window, then the
 * next space, so the passage starts at a word or line edge instead of
 * mid-token; with neither reachable, the cut stays exact.
 */
export function chapterRecentText(markdown: string): string {
  const normalized = String(markdown).replace(/\r\n?/g, "\n").trim();
  if (normalized.length <= RECENT_TEXT_CHARACTER_LIMIT) {
    return normalized;
  }
  const start = normalized.length - RECENT_TEXT_CHARACTER_LIMIT;
  const windowEnd = Math.min(normalized.length, start + RECENT_TEXT_BOUNDARY_WINDOW);
  const newlineAt = normalized.indexOf("\n", start);
  if (newlineAt >= start && newlineAt < windowEnd) {
    return normalized.slice(newlineAt + 1).trimStart();
  }
  const spaceAt = normalized.indexOf(" ", start);
  if (spaceAt >= start && spaceAt < windowEnd) {
    return normalized.slice(spaceAt + 1).trimStart();
  }
  return normalized.slice(start);
}

/**
 * The #312 reading order for chapters: owning-volume rank first, then
 * in-volume position; id breaks ties deterministically. Chapters whose
 * volume no longer resolves sort after all placed chapters.
 */
function compareChapters(
  ranks: Map<string, number>,
  left: ResidentChapterSource,
  right: ResidentChapterSource,
): number {
  const leftRank =
    left.volumeId === null
      ? Number.POSITIVE_INFINITY
      : (ranks.get(left.volumeId) ?? Number.POSITIVE_INFINITY);
  const rightRank =
    right.volumeId === null
      ? Number.POSITIVE_INFINITY
      : (ranks.get(right.volumeId) ?? Number.POSITIVE_INFINITY);
  return leftRank - rightRank || left.position - right.position || left.id.localeCompare(right.id);
}

/**
 * Assemble the resident view. Prior story covers every chapter strictly
 * before the target in reading order (a non-chapter or unknown target reads
 * as positionless, so all chapters precede it). The tail rule is uniform:
 * it always comes from the most recent story text OTHER than the target's
 * own manuscript — when drafting a next chapter that is the previous
 * chapter's ending; when continuing a chapter, that chapter's full current
 * text already rides verbatim in the untrusted manuscript block, so
 * repeating it would only duplicate what the model sees below.
 */
export function assembleResidentContext(source: ResidentContextSource): ResidentContextView {
  const ranks = new Map(source.volumes.map((volume, index) => [volume.id, index]));
  const ordered = source.chapters
    .filter((candidate) => candidate.kind === "chapter")
    .sort((left, right) => compareChapters(ranks, left, right));
  const targetIndex = ordered.findIndex((candidate) => candidate.id === source.targetDocumentId);
  const priors = targetIndex >= 0 ? ordered.slice(0, targetIndex) : ordered;

  const priorStory = priors.map((chapter, index) => ({
    ordinal: index + 1,
    title: chapter.title,
    digest:
      chapter.contentMarkdown !== null && chapter.contentMarkdown.trim() !== ""
        ? chapterDigest(chapter.contentMarkdown)
        : EMPTY_CHAPTER_DIGEST_PLACEHOLDER,
  }));

  let recentText: string | null = null;
  for (let index = priors.length - 1; index >= 0 && recentText === null; index -= 1) {
    const text = priors[index]?.contentMarkdown ?? "";
    if (text.trim() !== "") {
      recentText = chapterRecentText(text);
    }
  }

  return {
    outline:
      source.outlineMarkdown === null
        ? null
        : { markdown: source.outlineMarkdown, linkedBeat: source.linkedBeat },
    priorStory,
    recentText,
  };
}

/**
 * Gather the pure assembler's inputs from the project's own documents — never
 * across projects. The first outline-kind document in the composite reading
 * order remains the recorded authority (#313), and the beat link resolves
 * through the same splitter contract.
 */
export function collectResidentContextSource(
  store: StudioStore,
  scope: ProjectScope,
  projectId: string,
  document: DocumentWithCurrent,
): ResidentContextSource {
  const documents = store.findDocuments(scope, projectId);
  const outline = documents.find((candidate) => candidate.kind === "outline");
  return {
    outlineMarkdown: outline?.currentRevision?.contentMarkdown ?? null,
    linkedBeat: linkedChapterBeat(store, scope, projectId, document),
    volumes: store.findVolumes(scope, projectId),
    chapters: documents.map((candidate) => ({
      id: candidate.id,
      kind: candidate.kind,
      title: candidate.title,
      position: candidate.position,
      volumeId: candidate.volumeId,
      contentMarkdown: candidate.currentRevision?.contentMarkdown ?? null,
    })),
    targetDocumentId: document.id,
  };
}

/** The whole proposal user prompt: resident context, triggered lorebook, manuscript. */
export function buildProposalUserPrompt(
  input: {
    readonly operation: string;
    readonly instruction: string;
    readonly source: ResidentContextSource;
    readonly manuscriptMarkdown: string;
    /** Character/world entries (#315); matches render after the resident sections. */
    readonly loreEntries?: readonly LoreEntrySource[];
    /**
     * Character budget of the lorebook section (#445); defaults to the
     * adjudicated value. The single assembly point every proposal pipeline
     * (synchronous draft, SSE stream, retry) shares.
     */
    readonly loreBudgetCharacters?: number | undefined;
  },
  writer = new BoundedPromptWriter(),
): string {
  writer.writeLine(`Operation: ${input.operation}`);
  writer.writeLine(formatAuthorInstruction(input.instruction));
  const view = assembleResidentContext(input.source);
  for (const line of renderResidentContextSections(view)) writer.writeLine(line);
  for (const line of triggeredLoreSections({
    entries: input.loreEntries ?? [],
    resident: residentMatchCorpus(view),
    manuscript: input.manuscriptMarkdown,
    budgetCharacters: input.loreBudgetCharacters,
  }))
    writer.writeLine(line);
  writer.writeLine("");
  writer.writeLine("Current manuscript (untrusted JSON data):");
  writer.writeLine("");
  writer.writeLine(formatUntrustedManuscript(input.manuscriptMarkdown));
  return writer.finish();
}
