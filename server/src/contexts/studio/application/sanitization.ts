/**
 * The single table-driven sanitization source: every consumer of proposal
 * output sanitization or instruction scrubbing reads these tables. The data
 * mirrors the Python authority (service_common) so both stacks strip the
 * same adjudicated phrasing.
 */

/** Adjudicated mechanical phrases, exposed for prose guards and tests. */
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

/** The mechanical-phrase substitution table (pattern → replacement). */
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

/** Provider preamble lines that introduce mechanical output ("Here's the first draft…"). */
const MECHANICAL_PREAMBLE = new RegExp(
  `^\\s*(?:here(?:'s| is)|below is|sure[,!:]?|certainly[,!:]?|as requested[,!:]?|draft(?:ed)? chapter)\\b.*(?:${FORBIDDEN_TEMPLATE_ALTERNATION}).*$`,
  "i",
);

/** Instruction patterns adjudicated as prompt-injection attempts. */
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

/**
 * Neutralize adjudicated prompt-injection patterns in author instructions,
 * preserving the writing direction itself.
 */
export function sanitizeInstruction(instruction: string): string {
  let cleaned = instruction.trim();
  for (const pattern of PROMPT_INJECTION_PATTERNS) {
    cleaned = cleaned.replace(pattern, "[REDACTED]");
  }
  return cleaned;
}

/** Format an author instruction so it is structurally isolated in the prompt. */
export function formatAuthorInstruction(instruction: string): string {
  return `${AUTHOR_INSTRUCTION_BEGIN}\n${sanitizeInstruction(instruction)}\n${AUTHOR_INSTRUCTION_END}`;
}

/**
 * Encode manuscript text as an explicitly untrusted JSON data block. JSON
 * encoding keeps newlines and quotes inside the value boundary; brackets are
 * \u-escaped so manuscript text cannot manufacture a second delimiter.
 */
export function formatUntrustedManuscript(markdown: string): string {
  const payload = JSON.stringify({ content_markdown: String(markdown) }).replace(
    /([[\]])/g,
    (bracket) => `\\u00${bracket === "[" ? "5b" : "5d"}`,
  );
  return `${UNTRUSTED_MANUSCRIPT_BEGIN}\n${payload}\n${UNTRUSTED_MANUSCRIPT_END}`;
}

/**
 * Remove provider preambles and mechanical labels from a proposal before it
 * is returned or persisted, then normalize trailing spaces and blank-line
 * runs.
 */
export function sanitizeProposalMarkdown(markdown: string): string {
  // Line filtering reads LF-separated lines, so a CRLF preamble line must not
  // survive on the strength of its carriage return (Python: splitlines()).
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

/** Provider keys are deliberately limited to the two adjudicated scaffold labels. */
const PROVIDER_SCAFFOLDING_KEY =
  "(?:\"(?:echo|result)\"|'(?:echo|result)'|`(?:echo|result)`|(?:echo|result))";

/**
 * A provider key can begin a nested line or follow a Markdown/YAML list
 * marker. Horizontal whitespace is intentional: a line boundary is structural.
 */
const PROVIDER_SCAFFOLDING_LINE_KEY = new RegExp(
  `^[\\t ]*(?:(?:[-*+][\\t ]+(?:\\[[ xX]\\][\\t ]+)?)|(?:\\d+[.)][\\t ]+))?${PROVIDER_SCAFFOLDING_KEY}[\\t ]*(?::|=)`,
  "im",
);

type InlineContainer = "array" | "object";
type InlineStringDelimiter = '"' | "'" | "`";

function isInlineWhitespace(character: string | undefined): boolean {
  return character === " " || character === "\t" || character === "\r" || character === "\n";
}

function isInlineStringDelimiter(character: string): character is InlineStringDelimiter {
  return character === '"' || character === "'" || character === "`";
}

function isInlineIdentifierStart(character: string | undefined): boolean {
  return character !== undefined && /[A-Za-z_]/.test(character);
}

function isInlineIdentifierCharacter(character: string | undefined): boolean {
  return character !== undefined && /[A-Za-z0-9_-]/.test(character);
}

function startsInlineString(markdown: string, index: number): InlineStringDelimiter | undefined {
  const delimiter = markdown[index];
  if (delimiter === undefined || !isInlineStringDelimiter(delimiter)) return undefined;
  if (delimiter === "'" && isInlineIdentifierCharacter(markdown[index - 1])) return undefined;
  return delimiter;
}

/** Read a quoted or identifier key positioned directly after an object delimiter. */
function readsProviderScaffoldingObjectKey(markdown: string, start: number): boolean {
  let index = start;
  while (isInlineWhitespace(markdown[index])) index += 1;

  let key = "";
  const delimiter = markdown[index];
  if (delimiter !== undefined && isInlineStringDelimiter(delimiter)) {
    index += 1;
    let closed = false;
    for (; index < markdown.length; index += 1) {
      const character = markdown.charAt(index);
      if (character === "\\") {
        const escapedCharacter = markdown[index + 1];
        if (escapedCharacter === undefined) return false;
        if (escapedCharacter === "u") {
          const codePoint = markdown.slice(index + 2, index + 6);
          if (/^[0-9a-f]{4}$/i.test(codePoint)) {
            key += String.fromCharCode(Number.parseInt(codePoint, 16));
            index += 5;
            continue;
          }
        }
        key += escapedCharacter;
        index += 1;
      } else if (character === delimiter) {
        index += 1;
        closed = true;
        break;
      } else {
        key += character;
      }
    }
    if (!closed) return false;
  } else {
    if (!isInlineIdentifierStart(delimiter)) return false;
    do {
      key += markdown.charAt(index);
      index += 1;
    } while (isInlineIdentifierCharacter(markdown[index]));
  }

  while (isInlineWhitespace(markdown[index])) index += 1;
  const normalizedKey = key.toLowerCase();
  return (
    (normalizedKey === "echo" || normalizedKey === "result") &&
    (markdown[index] === ":" || markdown[index] === "=")
  );
}

/**
 * Scan object syntax lexically so a scaffold key after nested object or array
 * values remains structural, while commas and quotes in narrative prose do not.
 */
function hasProviderScaffoldingInlineObjectKey(markdown: string): boolean {
  const containers: InlineContainer[] = [];
  let stringDelimiter: InlineStringDelimiter | undefined;
  let escaped = false;

  for (let index = 0; index < markdown.length; index += 1) {
    const character = markdown.charAt(index);
    if (stringDelimiter !== undefined) {
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === stringDelimiter) {
        stringDelimiter = undefined;
      }
      continue;
    }

    const delimiter = startsInlineString(markdown, index);
    if (delimiter !== undefined) {
      stringDelimiter = delimiter;
      continue;
    }
    if (character === "{") {
      containers.push("object");
      if (readsProviderScaffoldingObjectKey(markdown, index + 1)) return true;
    } else if (character === "[") {
      containers.push("array");
    } else if (character === "}") {
      if (containers.length > 0 && containers.at(-1) !== "object") return true;
      containers.pop();
    } else if (character === "]") {
      if (containers.length > 0 && containers.at(-1) !== "array") return true;
      containers.pop();
    } else if (character === "," && containers.length > 0) {
      if (readsProviderScaffoldingObjectKey(markdown, index + 1)) return true;
    }
  }

  return false;
}

/**
 * Check the final, already-sanitized form of proposal markdown before a job
 * is completed. Residual mechanical output is rejected rather than rewritten.
 */
export function isProposalMarkdownProse(markdown: string): boolean {
  if (markdown.length <= 400 || parsesAsJson(markdown)) {
    return false;
  }

  if (
    PROVIDER_SCAFFOLDING_LINE_KEY.test(markdown) ||
    hasProviderScaffoldingInlineObjectKey(markdown)
  ) {
    return false;
  }

  const normalized = markdown.toLowerCase();
  return FORBIDDEN_PROSE_PHRASES.every((phrase) => !normalized.includes(phrase.toLowerCase()));
}
