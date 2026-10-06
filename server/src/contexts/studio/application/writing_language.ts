import type { WritingLanguage } from "../../../contexts/ai/application/ports/text_generation.js";
import type { ProposalContextSource } from "./ports/proposal_context_store.js";

/**
 * The project-scoped writing-language policy (DR-023). There is no persisted
 * locale field and no migration: the language is inferred deterministically
 * from the captured project text — every document title and current revision,
 * the outline included — and then injected into the generation prompt and the
 * provider task. A project whose text carries no script evidence keeps the
 * English default, so every pre-existing project behaves exactly as before.
 */

/** A Han code point: CJK Unified Ideographs and their extensions. */
const HAN_CHARACTER = /\p{Script=Han}/gu;
/** A Latin letter: the Latin side of the script-mass comparison. */
const LATIN_LETTER = /\p{Script=Latin}/gu;

/**
 * The minimum Han share of the total script mass for a Chinese project. One
 * Han character is one word while Latin words run several letters, so Han
 * text outweighs Latin text long before its character count does; a quarter
 * is conservative enough that an English chapter with a stray Han phrase
 * stays English, while an English-titled empty chapter beside a Chinese
 * outline still reads as Chinese.
 */
const HAN_SHARE_FOR_CHINESE = 0.25;

/** Infers the writing language of one text sample set; no samples means English. */
export function inferWritingLanguage(samples: readonly string[]): WritingLanguage {
  let han = 0;
  let latin = 0;
  for (const sample of samples) {
    han += sample.match(HAN_CHARACTER)?.length ?? 0;
    latin += sample.match(LATIN_LETTER)?.length ?? 0;
  }
  const scriptMass = han + latin;
  if (scriptMass === 0) return "en";
  return han / scriptMass >= HAN_SHARE_FOR_CHINESE ? "zh" : "en";
}

/**
 * The writing language of one captured proposal context. The whole captured
 * project weighs in on purpose: the target chapter may still be empty while
 * its outline, prior chapters, or lore entries already fix the language.
 */
export function projectWritingLanguage(context: ProposalContextSource): WritingLanguage {
  const samples: string[] = [];
  for (const document of context.documents) {
    samples.push(document.title);
    const markdown = document.currentRevision?.contentMarkdown;
    if (markdown !== undefined) samples.push(markdown);
  }
  return inferWritingLanguage(samples);
}
