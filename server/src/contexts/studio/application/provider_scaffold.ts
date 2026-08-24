type Quote = '"' | "'" | "`";
type JsonNode = { value: unknown; depth: number; layers: number };
const jsonLimits = { candidates: 512, candidateLength: 24e3, depth: 24 };
const walkLimits = { layers: 12, work: 512 };
const isWhitespace = (value?: string) => value !== undefined && /[\s\u0085\u200B]/u.test(value);
const isLineBreak = (v?: string) => v !== undefined && "\r\n\u0085\u2028\u2029".includes(v);
const isIdentifier = (value?: string) => /[A-Za-z0-9_-]/.test(value ?? "");
const isQuote = (value?: string): value is Quote => value === '"' || value === "'" || value === "`";
const isProviderKey = (key: string) => /^(echo|result)$/i.test(key);
const isInWordApostrophe = (markdown: string, index: number) =>
  markdown[index] === "'" && isIdentifier(markdown[index - 1]) && isIdentifier(markdown[index + 1]);
function skipWhitespace(markdown: string, index: number): number {
  while (isWhitespace(markdown[index])) index += 1;
  return index;
}
type UnicodeEscape = { character: string; end: number };
function readUnicodeEscape(markdown: string, index: number): UnicodeEscape | undefined {
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
function readField(markdown: string, start: number): { key: string; end: number } | undefined {
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
function readQuoteEnd(markdown: string, start: number): number | undefined {
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
const isStructuralToken = (v: string) => isWhitespace(v) || /[{}[\]"'`:=,;+*.)-]/.test(v);
function projectStructuralTokens(markdown: string): string {
  let projected = "";
  for (let index = 0; index < markdown.length; ) {
    const character = markdown[index] ?? "";
    const quotedEnd = isQuote(character) ? readQuoteEnd(markdown, index) : undefined;
    if (quotedEnd !== undefined) {
      projected += markdown.slice(index, quotedEnd);
      index = quotedEnd;
      continue;
    }
    if (character === "\\") {
      let slashEnd = index + 1;
      while (markdown[slashEnd] === "\\") slashEnd += 1;
      if (slashEnd > index + 1) {
        projected += markdown.slice(index, slashEnd);
        index = slashEnd;
        continue;
      }
      const unicodeEscape = readUnicodeEscape(markdown, index);
      const shortEscape = markdown[index + 1];
      const decoded = unicodeEscape?.character ?? shortEscape?.match(/["'`]/)?.[0];
      if (decoded !== undefined && isStructuralToken(decoded)) {
        projected += decoded;
        index = unicodeEscape?.end ?? index + 2;
        continue;
      }
    }
    projected += character;
    index += 1;
  }
  return projected;
}
function hasProjectedProviderJson(source: string): boolean {
  return hasSerializedProviderKey(parseSerializedJson(projectStructuralTokens(source)));
}
function hasQuotedProjectedJson(markdown: string): boolean {
  let candidates = 0;
  for (let index = 0; index < markdown.length; index += 1) {
    const quote = markdown[index];
    if (quote === '"') {
      const end = readQuoteEnd(markdown, index);
      if (end === undefined) continue;
      if (hasProjectedProviderJson(markdown.slice(index + 1, end - 1))) return true;
      index = end - 1;
    }
    if (quote !== "'" && quote !== "`") continue;
    if (isInWordApostrophe(markdown, index) || (quote === "`" && markdown.startsWith("```", index)))
      continue;
    const start = skipWhitespace(markdown, index + 1);
    const first = projectStructuralTokens(markdown.slice(start, start + 6))[0];
    if (first !== "{" && first !== "[" && first !== '"') continue;
    const limit = Math.min(markdown.length, index + jsonLimits.candidateLength + 1);
    for (let end = start; end < limit; end += 1) {
      if (markdown[end] === "\\") {
        end += 1;
      } else if (markdown[end] === quote) {
        if (++candidates > jsonLimits.candidates) return true;
        if (hasProjectedProviderJson(markdown.slice(index + 1, end))) return true;
      }
    }
    if (limit < markdown.length) return true;
  }
  return false;
}
function parseSerializedJson(source: string): unknown | undefined {
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
function readJsonStringEnd(markdown: string, start: number): number | "limit" | undefined {
  for (let index = start + 1; index < markdown.length; index += 1) {
    if (index - start > jsonLimits.candidateLength) return "limit";
    if (markdown[index] === '"') return index + 1;
    if (markdown[index] === "\\" && markdown[++index] === undefined) return undefined;
  }
  return undefined;
}
function readJsonCandidateEnd(markdown: string, start: number): number | "limit" | undefined {
  const first = markdown[start];
  if (first === '"') return readJsonStringEnd(markdown, start);
  if (first !== "{" && first !== "[") return undefined;
  const frames: Array<"}" | "]"> = [first === "{" ? "}" : "]"];
  for (let index = start + 1; index < markdown.length; index += 1) {
    if (index - start > jsonLimits.candidateLength) return "limit";
    const character = markdown[index];
    if (character === '"') {
      const end = readJsonStringEnd(markdown, index);
      if (end === undefined || end === "limit") return end;
      index = end - 1;
    } else if (character === "{" || character === "[") {
      frames.push(character === "{" ? "}" : "]");
    } else if (character === frames.at(-1)) {
      frames.pop();
      if (frames.length === 0) return index + 1;
    } else if (character === "}" || character === "]") return undefined;
  }
  return undefined;
}
function hasSerializedProviderKey(value: unknown): boolean {
  const worklist: JsonNode[] = [{ value, depth: 0, layers: 0 }];
  const seenStrings = new Set<string>();
  for (const [index, { value: candidateValue, depth, layers }] of worklist.entries()) {
    if (index >= walkLimits.work) return true;
    if (depth > jsonLimits.depth) return true;
    if (layers > walkLimits.layers) return true;
    if (typeof candidateValue === "string") {
      if (seenStrings.has(candidateValue)) continue;
      seenStrings.add(candidateValue);
      const start = skipWhitespace(candidateValue, 0);
      let end = candidateValue.length;
      while (end > start && isWhitespace(candidateValue[end - 1])) end -= 1;
      const quote = candidateValue[start];
      const source =
        (quote === "'" || quote === "`") && candidateValue[end - 1] === quote
          ? projectStructuralTokens(candidateValue.slice(start + 1, end - 1))
          : candidateValue;
      const decoded = parseSerializedJson(source);
      if (typeof decoded !== "string" && (decoded === null || typeof decoded !== "object"))
        continue;
      if (worklist.length >= walkLimits.work) return true;
      worklist.push({ value: decoded, depth: depth + 1, layers: layers + 1 });
      continue;
    }
    if (candidateValue === null || typeof candidateValue !== "object") continue;
    const entries = Object.entries(candidateValue);
    if (entries.some(([key]) => isProviderKey(key))) return true;
    if (worklist.length + entries.length > walkLimits.work) return true;
    for (const [, child] of entries) worklist.push({ value: child, depth: depth + 1, layers });
  }
  return false;
}
const isJsonOpeningFragment = (value: unknown) =>
  typeof value === "string" &&
  /^[\s\u0085\u200B]*[{[](?:[\s\u0085\u200B]*[{[])*[\s\u0085\u200B]*$/u.test(value);
function hasSerializedJsonScaffolding(markdown: string): boolean {
  let candidates = 0;
  for (let index = 0; index < markdown.length; index += 1) {
    if (!'"{['.includes(markdown[index] ?? "")) continue;
    const end = readJsonCandidateEnd(markdown, index);
    if (end === "limit" || ++candidates > jsonLimits.candidates) return true;
    if (end === undefined) continue;
    const decoded = parseSerializedJson(markdown.slice(index, end));
    if (decoded !== undefined && hasSerializedProviderKey(decoded)) return true;
    if (decoded !== undefined && !isJsonOpeningFragment(decoded)) index = end - 1;
  }
  return false;
}
const isFieldBoundary = (markdown: string, index: number) =>
  isWhitespace(markdown[index - 1]) || /[[{,}\]:="'`]/.test(markdown[index - 1] ?? "");
function hasLineKey(markdown: string, start: number): boolean {
  let index = skipWhitespace(markdown, start);
  if (/[+*-]/.test(markdown[index] ?? "") && isWhitespace(markdown[index + 1])) {
    index = skipWhitespace(markdown, index + 1);
    if (/^\[[ xX]\]/.test(markdown.slice(index))) index = skipWhitespace(markdown, index + 3);
  } else {
    const ordered = /^\d+[.)]/.exec(markdown.slice(index))?.[0];
    if (ordered !== undefined && isWhitespace(markdown[index + ordered.length])) {
      index = skipWhitespace(markdown, index + ordered.length);
    }
  }
  return isProviderKey(readField(markdown, index)?.key ?? "");
}
function scanComposite(markdown: string, start: number): number | true {
  const frames: Array<"}" | "]"> = [markdown[start] === "{" ? "}" : "]"];
  for (let index = start + 1; index < markdown.length; ) {
    const field = isFieldBoundary(markdown, index) ? readField(markdown, index) : undefined;
    if (field !== undefined) {
      if (isProviderKey(field.key)) return true;
      index = field.end;
      continue;
    }
    const quotedEnd = readQuoteEnd(markdown, index);
    if (quotedEnd !== undefined) {
      index = quotedEnd;
      continue;
    }
    const character = markdown[index];
    if (character === "{" || character === "[") {
      frames.push(character === "{" ? "}" : "]");
    } else if (character === frames.at(-1)) {
      frames.pop();
      if (frames.length === 0) {
        let continuation = index + 1;
        while (
          isWhitespace(markdown[continuation]) ||
          /[}\],;:=]/.test(markdown[continuation] ?? "")
        )
          continuation += 1;
        return isProviderKey(readField(markdown, continuation)?.key ?? "") ? true : index + 1;
      }
    }
    index += 1;
  }
  return markdown.length;
}
function hasDirectProviderScaffolding(markdown: string): boolean {
  if (hasSerializedJsonScaffolding(markdown)) return true;
  for (let index = 0; index < markdown.length; ) {
    if ((index === 0 || isLineBreak(markdown[index - 1])) && hasLineKey(markdown, index))
      return true;
    const character = markdown[index];
    if (character === "{" || character === "[") {
      const result = scanComposite(markdown, index);
      if (result === true) return true;
      index = result;
      continue;
    }
    const quotedEnd = readQuoteEnd(markdown, index);
    index = quotedEnd ?? index + 1;
  }
  return false;
}
export function hasProviderScaffolding(markdown: string): boolean {
  if (hasQuotedProjectedJson(markdown) || hasDirectProviderScaffolding(markdown)) return true;
  const projected = projectStructuralTokens(markdown);
  return projected !== markdown && hasDirectProviderScaffolding(projected);
}
