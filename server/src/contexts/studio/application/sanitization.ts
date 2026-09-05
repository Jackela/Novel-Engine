import { hasProviderScaffolding } from "./provider_scaffold.js";

/** Sanitization SSOT for proposal output and instruction scrubbing. */
export const FORBIDDEN_PROSE_PHRASES = [
  "revision anchor",
  "the chapter closes",
  "the next scene",
  "first draft",
  "rewritten chapter",
  "focus character",
  "focus_motivation",
  "relationship_status",
  "outline_hook",
] as const;
const MECHANICAL_SUBSTITUTIONS: readonly [RegExp, string][] = [
  [/revision anchor:\s*/gi, ""],
  [/\bthe chapter closes\b/gi, "The scene settles"],
  [/\bthe next scene\b/gi, "What follows"],
  [/\bfirst draft\b/gi, "opening passage"],
  [/\brewritten chapter\b/gi, "reworked passage"],
  [/\bfocus character\b/gi, "central figure"],
  [/\bfocus_motivation\b/gi, "central motivation"],
  [/\brelationship_status\b/gi, "relationship state"],
  [/\boutline_hook\b/gi, "story hook"],
];
const FORBIDDEN_TEMPLATE_ALTERNATION = FORBIDDEN_PROSE_PHRASES.map((phrase) =>
  phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
).join("|");
const MECHANICAL_PREAMBLE = new RegExp(
  `^\\s*(?:here(?:'s| is)|below is|sure[,!:]?|certainly[,!:]?|as requested[,!:]?|draft(?:ed)? chapter)\\b.*(?:${FORBIDDEN_TEMPLATE_ALTERNATION}).*$`,
  "i",
);
const PROMPT_INJECTION_PATTERNS: readonly RegExp[] = [
  /ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions/gi,
  /disregard\s+(?:all\s+)?(?:previous|prior|above)\s+instructions/gi,
  /new\s+system\s+prompt/gi,
  /you\s+are\s+now\s+(?:a|an|the)/gi,
  /override\s+(?:the\s+)?system\s+prompt/gi,
  /(?:act\s+as|pretend\s+to\s+be)\s+(?:a|an|the)/gi,
];
export const AUTHOR_INSTRUCTION_BEGIN = "[BEGIN AUTHOR INSTRUCTION]";
export const AUTHOR_INSTRUCTION_END = "[END AUTHOR INSTRUCTION]";
export const UNTRUSTED_MANUSCRIPT_BEGIN = "[BEGIN UNTRUSTED MANUSCRIPT JSON]";
export const UNTRUSTED_MANUSCRIPT_END = "[END UNTRUSTED MANUSCRIPT JSON]";
/** Resident-context section markers (#314, ADR-0004 layer 1). */
export const PROJECT_OUTLINE_BEGIN = "[BEGIN PROJECT OUTLINE]";
export const PROJECT_OUTLINE_END = "[END PROJECT OUTLINE]";
export const PRIOR_STORY_BEGIN = "[BEGIN PRIOR STORY SUMMARY]";
export const PRIOR_STORY_END = "[END PRIOR STORY SUMMARY]";
export const RECENT_TEXT_BEGIN = "[BEGIN RECENT CHAPTER TAIL]";
export const RECENT_TEXT_END = "[END RECENT CHAPTER TAIL]";
/** Keyword-triggered lorebook markers (#315, ADR-0004 layer 2). */
export const LOREBOOK_BEGIN = "[BEGIN LOREBOOK]";
export const LOREBOOK_END = "[END LOREBOOK]";

/**
 * Reversibly encode project-derived prompt data so it cannot emit a structural
 * block delimiter. Backslashes are escaped first, keeping a literal `\u005B`
 * distinct from an encoded opening bracket.
 */
export function escapePromptData(text: string): string {
  return String(text).replace(/\\/g, "\\\\").replace(/\[/g, "\\u005B").replace(/\]/g, "\\u005D");
}

export function sanitizeInstruction(instruction: string): string {
  let cleaned = instruction.trim();
  for (const pattern of PROMPT_INJECTION_PATTERNS) {
    cleaned = cleaned.replace(pattern, "[REDACTED]");
  }
  return cleaned;
}
export function formatAuthorInstruction(instruction: string): string {
  return `${AUTHOR_INSTRUCTION_BEGIN}\n${sanitizeInstruction(escapePromptData(instruction))}\n${AUTHOR_INSTRUCTION_END}`;
}
/** Escape square brackets so text cannot forge any bracketed prompt marker. */
export function escapePromptBlockMarkers(text: string): string {
  return String(text).replace(/([[\]])/g, (bracket) => `\\u00${bracket === "[" ? "5b" : "5d"}`);
}
/** Encode manuscript text as an explicitly untrusted, bracket-escaped JSON data block. */
export function formatUntrustedManuscript(markdown: string): string {
  const payload = JSON.stringify({ content_markdown: String(markdown) });
  return `${UNTRUSTED_MANUSCRIPT_BEGIN}\n${escapePromptBlockMarkers(payload)}\n${UNTRUSTED_MANUSCRIPT_END}`;
}
/** Encode chapter-derived reference prose without rewriting its story content. */
export function sanitizeResidentProse(text: string): string {
  return escapePromptData(text);
}
export function sanitizeProposalMarkdown(markdown: string): string {
  const kept = String(markdown)
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .filter((line) => !MECHANICAL_PREAMBLE.test(line));
  let cleaned = kept.join("\n");
  for (const [pattern, replacement] of MECHANICAL_SUBSTITUTIONS) {
    cleaned = cleaned.replace(pattern, replacement);
  }
  return cleaned
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
function parsesAsJson(markdown: string): boolean {
  try {
    JSON.parse(markdown);
    return true;
  } catch (error) {
    if (error instanceof SyntaxError) {
      return false;
    }
    throw error;
  }
}
/** Reject residual provider scaffolding before a proposal job is completed. */
export function isProposalMarkdownProse(markdown: string): boolean {
  if (markdown.length <= 400 || parsesAsJson(markdown)) {
    return false;
  }
  if (hasProviderScaffolding(markdown)) {
    return false;
  }
  const normalized = markdown.toLowerCase();
  return FORBIDDEN_PROSE_PHRASES.every((phrase) => !normalized.includes(phrase.toLowerCase()));
}
