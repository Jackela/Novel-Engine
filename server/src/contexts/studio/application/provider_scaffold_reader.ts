export type Quote = '"' | "'" | "`";
export type UnicodeEscape = { character: string; end: number };

/**
 * Outcome of reading a JSON candidate boundary.
 * `end` carries the exclusive end index of a well-formed candidate,
 * `limit` means the candidate exceeded the scan budget (treated as
 * scaffolding by callers), `none` means no well-formed candidate.
 */
export type CandidateEnd = { kind: "end"; end: number } | { kind: "limit" } | { kind: "none" };

export const jsonLimits = { candidates: 512, candidateLength: 24e3, depth: 24 };
export const isWhitespace = (value?: string) =>
  value !== undefined && /[\s\u0085\u200B]/u.test(value);
export const isLineBreak = (v?: string) => v !== undefined && "\r\n\u0085\u2028\u2029".includes(v);
export const isIdentifier = (value?: string) => /[A-Za-z0-9_-]/.test(value ?? "");
export const isQuote = (value?: string): value is Quote =>
  value === '"' || value === "'" || value === "`";
export const isInWordApostrophe = (markdown: string, index: number) =>
  markdown[index] === "'" && isIdentifier(markdown[index - 1]) && isIdentifier(markdown[index + 1]);
export function skipWhitespace(markdown: string, index: number): number {
  while (isWhitespace(markdown[index])) index += 1;
  return index;
}
export function readUnicodeEscape(markdown: string, index: number): UnicodeEscape | undefined {
  const codePoint = markdown.slice(index + 2, index + 6);
  if (!markdown.startsWith("\\u", index) || !/^[0-9a-f]{4}$/i.test(codePoint)) return undefined;
  return { character: String.fromCharCode(Number.parseInt(codePoint, 16)), end: index + 6 };
}
const isKeyCharacter = (v: string, f: boolean) => (f ? /[A-Za-z_]/ : /[A-Za-z0-9_-]/).test(v);
function readSeparator(markdown: string, index: number): number | undefined {
  const unicodeEscape = readUnicodeEscape(markdown, index);
  const character = markdown[index] === "\\" ? unicodeEscape?.character : markdown[index];
  return character === ":" || character === "=" ? (unicodeEscape?.end ?? index + 1) : undefined;
}
export function readField(
  markdown: string,
  start: number,
): { key: string; end: number } | undefined {
  const delimiter = markdown[start],
    quoted = isQuote(delimiter);
  let index = quoted ? start + 1 : start;
  let key = "";
  while (index < markdown.length) {
    const character = markdown[index] ?? "";
    if (quoted && character === delimiter) {
      index += 1;
      break;
    }
    const unicodeEscape = character === "\\" ? readUnicodeEscape(markdown, index) : undefined;
    if (character === "\\" && unicodeEscape === undefined) return undefined;
    const decoded = unicodeEscape?.character ?? character;
    if (!quoted && key.length > 0 && /[:=]/.test(decoded)) break;
    if (!quoted && !isKeyCharacter(decoded, key.length === 0)) {
      if (unicodeEscape !== undefined) return undefined;
      break;
    }
    key += decoded;
    index = unicodeEscape?.end ?? index + 1;
  }
  if ((quoted && markdown[index - 1] !== delimiter) || key.length === 0) return undefined;
  index = skipWhitespace(markdown, index);
  if (!quoted && isQuote(markdown[index]) && readSeparator(markdown, index + 1) !== undefined)
    index += 1;
  const end = readSeparator(markdown, index);
  return end === undefined ? undefined : { key, end };
}
export function readQuoteEnd(markdown: string, start: number): number | undefined {
  const delimiter = markdown[start];
  if (!isQuote(delimiter) || isInWordApostrophe(markdown, start)) return undefined;
  if (delimiter === "`" && markdown.startsWith("```", start)) return start + 3;
  for (let index = start + 1; index < markdown.length; index += 1) {
    const character = markdown[index];
    if (character === "\\") {
      const escaped = markdown[index + 1];
      const unicodeEscape = escaped === "u" ? readUnicodeEscape(markdown, index) : true;
      if (escaped === undefined || unicodeEscape === undefined) return undefined;
      index += escaped === "u" ? 5 : 1;
    } else if (character === delimiter && !isInWordApostrophe(markdown, index)) return index + 1;
  }
  return undefined;
}
export function parseSerializedJson(source: string): unknown | undefined {
  let quoted = false;
  let escaped = false;
  let normalized = "";
  for (const character of source) {
    normalized += !quoted && isWhitespace(character) ? " " : character;
    if (quoted && escaped) escaped = false;
    else if (quoted && character === "\\") escaped = true;
    else if (character === '"') quoted = !quoted;
  }
  try {
    return JSON.parse(normalized) as unknown;
  } catch {
    return undefined;
  }
}
export function readJsonStringEnd(markdown: string, start: number): CandidateEnd {
  for (let index = start + 1; index < markdown.length; index += 1) {
    if (index - start > jsonLimits.candidateLength) return { kind: "limit" };
    if (markdown[index] === '"') return { kind: "end", end: index + 1 };
    if (markdown[index] === "\\" && markdown[++index] === undefined) return { kind: "none" };
  }
  return { kind: "none" };
}
export function readJsonCandidateEnd(markdown: string, start: number): CandidateEnd {
  const first = markdown[start];
  if (first === '"') return readJsonStringEnd(markdown, start);
  if (first !== "{" && first !== "[") return { kind: "none" };
  const frames: Array<"}" | "]"> = [first === "{" ? "}" : "]"];
  for (let index = start + 1; index < markdown.length; index += 1) {
    if (index - start > jsonLimits.candidateLength) return { kind: "limit" };
    const character = markdown[index];
    if (character === '"') {
      const end = readJsonStringEnd(markdown, index);
      if (end.kind !== "end") return end;
      index = end.end - 1;
    } else if (character === "{" || character === "[") {
      frames.push(character === "{" ? "}" : "]");
    } else if (character === frames.at(-1)) {
      frames.pop();
      if (frames.length === 0) return { kind: "end", end: index + 1 };
    } else if (character === "}" || character === "]") return { kind: "none" };
  }
  return { kind: "none" };
}
