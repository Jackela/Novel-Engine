type Quote = '"' | "'" | "`";
type JsonNode = { value: unknown; depth: number; stringLayers: number };
type JsonEnd = number | "limit" | undefined;
const jsonLimits = {
  candidates: 512,
  candidateLength: 24_000,
  depth: 24,
  stringLayers: 12,
  work: 512,
};
const isWhitespace = (character: string | undefined) =>
  character === "\u200B" ||
  character === "\u0085" ||
  (character !== undefined && /^\s$/u.test(character));
const isLineBreak = (character: string | undefined) =>
  character !== undefined && "\r\n\u0085\u2028\u2029".includes(character);
const isIdentifier = (character: string | undefined) => /[A-Za-z0-9_-]/.test(character ?? "");
const isQuote = (character: string | undefined): character is Quote =>
  character === '"' || character === "'" || character === "`";
const isProviderKey = (key: string) =>
  key.toLowerCase() === "echo" || key.toLowerCase() === "result";
function skipWhitespace(markdown: string, index: number): number {
  while (isWhitespace(markdown[index])) index += 1;
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
function isKeyCharacter(character: string, first: boolean): boolean {
  return (first ? /[A-Za-z_]/ : /[A-Za-z0-9_-]/).test(character);
}
function readSeparator(markdown: string, index: number): number | undefined {
  if (markdown[index] === ":" || markdown[index] === "=") return index + 1;
  const unicodeEscape = readUnicodeEscape(markdown, index);
  return unicodeEscape !== undefined &&
    (unicodeEscape.character === ":" || unicodeEscape.character === "=")
    ? unicodeEscape.end
    : undefined;
}
function readField(markdown: string, start: number): { key: string; end: number } | undefined {
  const delimiter = markdown[start];
  const quoted = isQuote(delimiter);
  let index = quoted ? start + 1 : start;
  let key = "";
  while (index < markdown.length) {
    const character = markdown[index] ?? "";
    if (quoted && character === delimiter) {
      index += 1;
      break;
    }
    if (character === "\\") {
      const unicodeEscape = readUnicodeEscape(markdown, index);
      if (unicodeEscape === undefined) return undefined;
      if (!quoted && key.length > 0 && /[:=]/.test(unicodeEscape.character)) break;
      if (!quoted && !isKeyCharacter(unicodeEscape.character, key.length === 0)) return undefined;
      key += unicodeEscape.character;
      index = unicodeEscape.end;
      continue;
    }
    if (!quoted && !isKeyCharacter(character, key.length === 0)) break;
    key += character;
    index += 1;
  }
  if ((quoted && markdown[index - 1] !== delimiter) || key.length === 0) return undefined;
  index = skipWhitespace(markdown, index);
  if (!quoted && isQuote(markdown[index]) && readSeparator(markdown, index + 1) !== undefined) {
    index += 1;
  }
  const end = readSeparator(markdown, index);
  return end === undefined ? undefined : { key, end };
}
function readQuoteEnd(markdown: string, start: number): number | undefined {
  const delimiter = markdown[start];
  if (!isQuote(delimiter)) return undefined;
  if (delimiter === "`" && markdown.startsWith("```", start)) return start + 3;
  if (delimiter === "'" && isIdentifier(markdown[start - 1]) && isIdentifier(markdown[start + 1])) {
    return undefined;
  }
  for (let index = start + 1; index < markdown.length; index += 1) {
    const character = markdown[index];
    if (character === "\\") {
      const escaped = markdown[index + 1];
      if (
        escaped === undefined ||
        (escaped === "u" && readUnicodeEscape(markdown, index) === undefined)
      )
        return undefined;
      index += escaped === "u" ? 5 : 1;
    } else if (
      character === delimiter &&
      !(delimiter === "'" && isIdentifier(markdown[index - 1]) && isIdentifier(markdown[index + 1]))
    ) {
      return index + 1;
    }
  }
  return undefined;
}
function normalizeSerializedJsonWhitespace(source: string): string {
  let quoted = false;
  let escaped = false;
  let normalized = "";
  for (const character of source) {
    normalized += !quoted && isWhitespace(character) ? " " : character;
    if (quoted && escaped) escaped = false;
    else if (quoted && character === "\\") escaped = true;
    else if (character === '"') quoted = !quoted;
  }
  return normalized;
}
function parseSerializedJson(source: string): unknown | undefined {
  try {
    return JSON.parse(normalizeSerializedJsonWhitespace(source)) as unknown;
  } catch {
    return undefined;
  }
}
function readJsonStringEnd(markdown: string, start: number): JsonEnd {
  for (let index = start + 1; index < markdown.length; index += 1) {
    if (index - start > jsonLimits.candidateLength) return "limit";
    if (markdown[index] === "\\") {
      if (markdown[index + 1] === undefined) return undefined;
      index += 1;
    } else if (markdown[index] === '"') return index + 1;
  }
  return undefined;
}
function readJsonCandidateEnd(markdown: string, start: number): JsonEnd {
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
  const worklist: JsonNode[] = [{ value, depth: 0, stringLayers: 0 }];
  const seenStrings = new Set<string>();
  for (const [index, candidate] of worklist.entries()) {
    if (index >= jsonLimits.work) return true;
    if (candidate.depth > jsonLimits.depth) return true;
    if (candidate.stringLayers > jsonLimits.stringLayers) return true;
    if (typeof candidate.value === "string") {
      if (seenStrings.has(candidate.value)) continue;
      seenStrings.add(candidate.value);
      const decoded = parseSerializedJson(candidate.value);
      if (
        typeof decoded === "string" ||
        Array.isArray(decoded) ||
        (decoded !== null && typeof decoded === "object")
      ) {
        if (worklist.length >= jsonLimits.work) return true;
        worklist.push({
          value: decoded,
          depth: candidate.depth + 1,
          stringLayers: candidate.stringLayers + 1,
        });
      }
      continue;
    }
    const children = Array.isArray(candidate.value)
      ? candidate.value.map((child) => [undefined, child] as const)
      : candidate.value !== null && typeof candidate.value === "object"
        ? Object.entries(candidate.value)
        : [];
    if (children.some(([key]) => key !== undefined && isProviderKey(key))) return true;
    if (worklist.length + children.length > jsonLimits.work) return true;
    for (const [, child] of children) {
      worklist.push({
        value: child,
        depth: candidate.depth + 1,
        stringLayers: candidate.stringLayers,
      });
    }
  }
  return false;
}
function hasSerializedJsonScaffolding(markdown: string): boolean {
  let candidates = 0;
  for (let index = 0; index < markdown.length; ) {
    const start = markdown[index];
    if (start !== '"' && start !== "{" && start !== "[") {
      index += 1;
      continue;
    }
    const end = readJsonCandidateEnd(markdown, index);
    if (end === "limit" || ++candidates > jsonLimits.candidates) return true;
    if (end === undefined) {
      index += 1;
      continue;
    }
    const decoded = parseSerializedJson(markdown.slice(index, end));
    if (decoded !== undefined && hasSerializedProviderKey(decoded)) return true;
    index = decoded === undefined ? index + 1 : end;
  }
  return false;
}
function isFieldBoundary(markdown: string, index: number): boolean {
  const previous = markdown[index - 1];
  return previous === undefined || isWhitespace(previous) || /[[{,}\]:="'`]/.test(previous);
}
function hasLineKey(markdown: string, start: number): boolean {
  let index = start;
  while (isWhitespace(markdown[index])) index += 1;
  if (/[+*-]/.test(markdown[index] ?? "") && isWhitespace(markdown[index + 1])) {
    index = skipWhitespace(markdown, index + 1);
    if (
      markdown[index] === "[" &&
      /[ xX]/.test(markdown[index + 1] ?? "") &&
      markdown[index + 2] === "]"
    ) {
      index = skipWhitespace(markdown, index + 3);
    }
  } else {
    const orderedStart = index;
    while (/\d/.test(markdown[index] ?? "")) index += 1;
    index =
      index > orderedStart &&
      /[.)]/.test(markdown[index] ?? "") &&
      isWhitespace(markdown[index + 1])
        ? skipWhitespace(markdown, index + 1)
        : orderedStart;
  }
  const field = readField(markdown, index);
  return field !== undefined && isProviderKey(field.key);
}
function hasLooseContinuation(markdown: string, start: number): boolean {
  let index = start;
  while (isWhitespace(markdown[index]) || /[}\],;:=]/.test(markdown[index] ?? "")) index += 1;
  const field = readField(markdown, index);
  return field !== undefined && isProviderKey(field.key);
}
function scanComposite(markdown: string, start: number): number | true {
  const frames = [{ closer: markdown[start] === "{" ? "}" : "]" }];
  for (let index = start + 1; index < markdown.length; ) {
    if (isFieldBoundary(markdown, index)) {
      const field = readField(markdown, index);
      if (field !== undefined) {
        if (isProviderKey(field.key)) return true;
        index = field.end;
        continue;
      }
    }
    const quotedEnd = readQuoteEnd(markdown, index);
    if (quotedEnd !== undefined) {
      index = quotedEnd;
      continue;
    }
    const character = markdown[index];
    if (character === "{" || character === "[") {
      frames.push({ closer: character === "{" ? "}" : "]" });
    } else if (character === frames.at(-1)?.closer) {
      frames.pop();
      if (frames.length === 0) {
        const end = index + 1;
        return hasLooseContinuation(markdown, end) ? true : end;
      }
    }
    index += 1;
  }
  return markdown.length;
}
export function hasProviderScaffolding(markdown: string): boolean {
  if (hasSerializedJsonScaffolding(markdown)) return true;
  for (let index = 0; index < markdown.length; ) {
    if ((index === 0 || isLineBreak(markdown[index - 1])) && hasLineKey(markdown, index)) {
      return true;
    }
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
