import { HARD_DEFAULT_MODELS } from "../../application/model_resolution.js";
import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationResult,
  type TextGenerationStreamOptions,
  type TextGenerationTask,
  type TextProviderName,
} from "../../application/ports/text_generation.js";
import {
  buildEditorialReview,
  buildLoreExtractCandidates,
} from "./deterministic_review_content.js";
import { buildChapterDraft, buildChapterRevision } from "./deterministic_story_content.js";

/** #308: deltas carry small word groups so consumers see progressive text. */
const STREAM_WORDS_PER_DELTA = 4;

/**
 * #308 streaming boundary: whitespace is captured by the split so joined
 * deltas equal the source; adjacent Han characters split too (DR-023) so
 * Chinese prose streams in small character groups instead of one monolithic
 * delta, while Latin-only text keeps byte-identical deltas. The capture
 * wraps the whole alternation so a Han boundary captures "" instead of the
 * `undefined` a partial capture group would inject.
 */
const STREAM_PIECE_BOUNDARY = /((?:\s+)|(?<=\p{Script=Han})(?=\p{Script=Han}))/u;

/**
 * Deterministic (mock) provider: real prose for the chapter steps — English
 * or Chinese according to the task's writing language (DR-023) — deterministic
 * dimensioned findings for the review step, and fixed placeholder lore
 * candidates for the lore-extract step, so the offline default experience
 * yields manuscripts, reviews, and wizard candidates without network. Any
 * step outside its supported set fails with a provider error — an unknown
 * step is never echoed back as a placeholder payload.
 */
export class DeterministicStoryProvider implements TextGenerationProvider {
  private readonly providerName: TextProviderName;
  private readonly model: string;

  constructor(providerName: TextProviderName = "mock", model: string = HARD_DEFAULT_MODELS.mock) {
    this.providerName = providerName;
    this.model = model;
  }

  async generateStructured(task: TextGenerationTask): Promise<TextGenerationResult> {
    const step = task.step.trim().toLowerCase();
    if (step === "editorial_review") {
      const findings = buildEditorialReview(task);
      const rawText = JSON.stringify(findings);
      return {
        step: task.step,
        provider: this.providerName,
        model: this.model,
        rawText,
        content: findings,
        promptTokens: null,
        completionTokens: null,
      };
    }
    if (step === "lore_extract") {
      const candidates = buildLoreExtractCandidates(task);
      return {
        step: task.step,
        provider: this.providerName,
        model: this.model,
        rawText: JSON.stringify(candidates),
        content: candidates,
        promptTokens: null,
        completionTokens: null,
      };
    }
    let markdown: string;
    if (step === "chapter_draft") {
      markdown = buildChapterDraft(task);
    } else if (step === "chapter_revision") {
      markdown = buildChapterRevision(task);
    } else {
      throw new TextGenerationProviderError(`Unsupported generation step: ${task.step}`);
    }
    return {
      step: task.step,
      provider: this.providerName,
      model: this.model,
      rawText: markdown,
      content: { chapter_markdown: markdown },
      promptTokens: null,
      completionTokens: null,
    };
  }

  /**
   * Streams the same fixed prose as `generateStructured` in small word (or,
   * for Chinese, character) groups; joining every delta reproduces the chapter
   * markdown byte-for-byte, so the streaming path stays assertable against the
   * synchronous contract.
   */
  async *generateStructuredStreaming(
    task: TextGenerationTask,
    options?: TextGenerationStreamOptions,
  ): AsyncGenerator<string, void, void> {
    const step = task.step.trim().toLowerCase();
    let markdown: string;
    if (step === "chapter_draft") {
      markdown = buildChapterDraft(task);
    } else if (step === "chapter_revision") {
      markdown = buildChapterRevision(task);
    } else {
      throw new TextGenerationProviderError(`Unsupported generation step: ${task.step}`);
    }
    let pending = "";
    let words = 0;
    for (const piece of markdown.split(STREAM_PIECE_BOUNDARY)) {
      if (options?.signal?.aborted === true) return;
      pending += piece;
      if (piece.trim() !== "") words += 1;
      if (words >= STREAM_WORDS_PER_DELTA && pending !== "") {
        yield pending;
        pending = "";
        words = 0;
      }
    }
    if (pending !== "") yield pending;
    if (options?.signal?.aborted === true) return;
    options?.onOutcome?.({ model: this.model, promptTokens: null, completionTokens: null });
  }
}
