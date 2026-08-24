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
export function sanitizeInstruction(instruction: string): string {
  let cleaned = instruction.trim();
  for (const pattern of PROMPT_INJECTION_PATTERNS) {
    cleaned = cleaned.replace(pattern, "[REDACTED]");
  }
  return cleaned;
}
export function formatAuthorInstruction(instruction: string): string {
  return `${AUTHOR_INSTRUCTION_BEGIN}\n${sanitizeInstruction(instruction)}\n${AUTHOR_INSTRUCTION_END}`;
}
/** Encode manuscript text as an explicitly untrusted, bracket-escaped JSON data block. */
export function formatUntrustedManuscript(markdown: string): string {
  const payload = JSON.stringify({ content_markdown: String(markdown) }).replace(
    /([[\]])/g,
    (bracket) => `\\u00${bracket === "[" ? "5b" : "5d"}`,
  );
  return `${UNTRUSTED_MANUSCRIPT_BEGIN}\n${payload}\n${UNTRUSTED_MANUSCRIPT_END}`;
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
type Quote = '"' | "'" | "`";
type KeyRead = { key: string; end: number } | { invalid: true } | undefined;
type Frame = { type: "array" | "object"; state: string };
const isWhitespace = (character: string | undefined) => /[ \t\r\n]/.test(character ?? "");
const isHorizontalWhitespace = (character: string | undefined) =>
  character === " " || character === "\t";
const isQuote = (character: string | undefined): character is Quote =>
  character === '"' || character === "'" || character === "`";
const isKeyCharacter = (character: string, first: boolean) =>
  (first ? /[A-Za-z_]/ : /[A-Za-z0-9_-]/).test(character);
const isProviderKey = (key: string) =>
  key.toLowerCase() === "echo" || key.toLowerCase() === "result";
function skipWhitespace(markdown: string, index: number): number {
  while (isWhitespace(markdown[index])) index += 1;
  return index;
}
function skipHorizontalWhitespace(markdown: string, index: number): number {
  while (isHorizontalWhitespace(markdown[index])) index += 1;
  return index;
}
function readUnicodeEscape(
  markdown: string,
  index: number,
): { character: string; end: number } | undefined {
  const codePoint = markdown.slice(index + 2, index + 6);
  return markdown[index] === "\\" && markdown[index + 1] === "u" && /^[0-9a-f]{4}$/i.test(codePoint)
    ? { character: String.fromCharCode(Number.parseInt(codePoint, 16)), end: index + 6 }
    : undefined;
}
function readStructuralKey(markdown: string, start: number): KeyRead {
  const delimiter = markdown[start];
  let index = isQuote(delimiter) ? start + 1 : start;
  let key = "";
  while (index < markdown.length) {
    let character = markdown[index] ?? "";
    if (isQuote(delimiter) && character === delimiter) return { key, end: index + 1 };
    if (character === "\\") {
      const unicode = readUnicodeEscape(markdown, index);
      if (unicode === undefined) return { invalid: true };
      character = unicode.character;
      index = unicode.end;
    } else {
      if (!isQuote(delimiter) && !isKeyCharacter(character, key.length === 0)) break;
      key += character;
      index += 1;
      continue;
    }
    if (!isQuote(delimiter) && !isKeyCharacter(character, key.length === 0))
      return { invalid: true };
    key += character;
  }
  return isQuote(delimiter)
    ? { invalid: true }
    : key.length === 0
      ? undefined
      : { key, end: index };
}
function readKeyAndSeparator(markdown: string, start: number): KeyRead {
  const key = readStructuralKey(markdown, start);
  if (key === undefined || "invalid" in key) return key;
  const end = skipWhitespace(markdown, key.end);
  return markdown[end] === ":" || markdown[end] === "="
    ? { key: key.key, end: end + 1 }
    : undefined;
}
function hasProviderScaffoldingLineKey(markdown: string, start: number): boolean {
  let index = start;
  while (isHorizontalWhitespace(markdown[index])) index += 1;
  if (/[+*-]/.test(markdown[index] ?? "") && isHorizontalWhitespace(markdown[index + 1])) {
    index = skipHorizontalWhitespace(markdown, index + 1);
    if (
      markdown[index] === "[" &&
      /[ xX]/.test(markdown[index + 1] ?? "") &&
      markdown[index + 2] === "]"
    )
      index = skipHorizontalWhitespace(markdown, index + 3);
  } else {
    const orderedStart = index;
    while (/\d/.test(markdown[index] ?? "")) index += 1;
    index =
      index > orderedStart &&
      /[.)]/.test(markdown[index] ?? "") &&
      isHorizontalWhitespace(markdown[index + 1])
        ? skipHorizontalWhitespace(markdown, index + 1)
        : orderedStart;
  }
  const key = readKeyAndSeparator(markdown, index);
  return key !== undefined && !("invalid" in key) && isProviderKey(key.key);
}
function readQuotedEnd(markdown: string, start: number): number | undefined {
  const delimiter = markdown[start];
  if (!isQuote(delimiter)) return undefined;
  for (let index = start + 1; index < markdown.length; index += 1) {
    if (markdown[index] === "\\") index += 1;
    else if (markdown[index] === delimiter) return index + 1;
  }
  return undefined;
}
function closeFrame(frames: Frame[]): void {
  frames.pop();
  const parent = frames.at(-1);
  if (parent !== undefined) parent.state = "after";
}
/** Parse a structural candidate as object/array states and fail closed on malformed syntax. */
function readStructuralCandidate(markdown: string, start: number): number | undefined {
  const frames: Frame[] = [{ type: "object", state: "key" }];
  for (let index = start + 1; index < markdown.length; ) {
    const frame = frames.at(-1);
    if (frame === undefined) return undefined;
    index = skipWhitespace(markdown, index);
    const character = markdown[index];
    if (frame.state === "key" || frame.state === "key-or-close") {
      if (character === "}" && frame.state === "key-or-close") {
        closeFrame(frames);
        index += 1;
      } else {
        const key = readStructuralKey(markdown, index);
        if (key === undefined || "invalid" in key || isProviderKey(key.key)) return undefined;
        frame.state = "separator";
        index = key.end;
        continue;
      }
    } else if (frame.state === "separator") {
      if (character !== ":" && character !== "=") return undefined;
      frame.state = "value";
      index += 1;
      continue;
    } else if (frame.state === "value" || frame.state === "value-or-close") {
      if (character === "]" && frame.state === "value-or-close") {
        closeFrame(frames);
        index += 1;
      } else if (character === "{" || character === "[") {
        frames.push({
          type: character === "{" ? "object" : "array",
          state: character === "{" ? "key-or-close" : "value-or-close",
        });
        index += 1;
        continue;
      } else if (character === undefined || /[,}\]]/.test(character)) {
        return undefined;
      } else if (isQuote(character)) {
        const end = readQuotedEnd(markdown, index);
        if (end === undefined) return undefined;
        frame.state = "after";
        index = end;
        continue;
      } else {
        const valueStart = index;
        while (index < markdown.length && !/[,}\]]/.test(markdown[index] ?? "")) {
          if (markdown[index] === ":" || markdown[index] === "=") return undefined;
          index += 1;
        }
        if (index === valueStart) return undefined;
        frame.state = "after";
        continue;
      }
    } else if (character === ",") {
      frame.state = frame.type === "object" ? "key" : "value";
      index += 1;
      continue;
    } else if (character === (frame.type === "object" ? "}" : "]")) {
      closeFrame(frames);
      index += 1;
    } else {
      return undefined;
    }
    if (frames.length === 0) return index;
  }
  return undefined;
}
function hasProviderScaffolding(markdown: string): boolean {
  let afterCandidate = false;
  for (let index = 0; index < markdown.length; ) {
    if (
      (index === 0 || /[\r\n]/.test(markdown[index - 1] ?? "")) &&
      hasProviderScaffoldingLineKey(markdown, index)
    )
      return true;
    const character = markdown[index] ?? "";
    if (afterCandidate) {
      if (isWhitespace(character)) {
        index += 1;
        continue;
      }
      if (character === "}" || character === "]") return true;
      afterCandidate = false;
    }
    const key =
      character === "{"
        ? readKeyAndSeparator(markdown, skipWhitespace(markdown, index + 1))
        : undefined;
    if (key !== undefined && !("invalid" in key)) {
      const end = readStructuralCandidate(markdown, index);
      if (end === undefined) return true;
      index = end;
      afterCandidate = true;
    } else if (character === '"' || character === "`") {
      index = readQuotedEnd(markdown, index) ?? index + 1;
    } else {
      index += 1;
    }
  }
  return false;
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
