type Quote = '"' | "'" | "`";
type Field = { key: string; end: number } | undefined;
type Frame = { closer: "}" | "]" };

const isWhitespace = (character: string | undefined) =>
  character !== undefined && /^\s$/u.test(character);
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

function readField(markdown: string, start: number): Field {
  const delimiter = markdown[start];
  let index = isQuote(delimiter) ? start + 1 : start;
  let key = "";
  while (index < markdown.length) {
    let character = markdown[index] ?? "";
    if (isQuote(delimiter) && character === delimiter) {
      index += 1;
      break;
    }
    if (character === "\\") {
      const unicodeEscape = readUnicodeEscape(markdown, index);
      if (unicodeEscape === undefined) return undefined;
      character = unicodeEscape.character;
      index = unicodeEscape.end;
    } else {
      if (!isQuote(delimiter) && !isKeyCharacter(character, key.length === 0)) break;
      key += character;
      index += 1;
      continue;
    }
    if (!isQuote(delimiter) && !isKeyCharacter(character, key.length === 0)) return undefined;
    key += character;
  }
  if ((isQuote(delimiter) && markdown[index - 1] !== delimiter) || key.length === 0)
    return undefined;
  index = skipWhitespace(markdown, index);
  if (!isQuote(delimiter) && isQuote(markdown[index]) && /[:=]/.test(markdown[index + 1] ?? "")) {
    index += 1;
  }
  return markdown[index] === ":" || markdown[index] === "=" ? { key, end: index + 1 } : undefined;
}

function readQuoteEnd(markdown: string, start: number): number | undefined {
  const delimiter = markdown[start];
  if (!isQuote(delimiter)) return undefined;
  if (delimiter === "'" && isIdentifier(markdown[start - 1]) && isIdentifier(markdown[start + 1])) {
    return undefined;
  }
  for (let index = start + 1; index < markdown.length; index += 1) {
    const character = markdown[index];
    if (character === "\\") {
      const unicodeEscape = readUnicodeEscape(markdown, index);
      if (
        markdown[index + 1] === undefined ||
        (markdown[index + 1] === "u" && unicodeEscape === undefined)
      ) {
        return undefined;
      }
      index = unicodeEscape === undefined ? index + 1 : unicodeEscape.end - 1;
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

function hasSerializedProviderKey(value: object | unknown[]): boolean {
  const worklist: unknown[] = [value];
  while (worklist.length > 0) {
    const candidate = worklist.pop();
    if (Array.isArray(candidate)) {
      worklist.push(...candidate);
      continue;
    }
    if (candidate === null || typeof candidate !== "object") continue;
    for (const [key, child] of Object.entries(candidate)) {
      if (isProviderKey(key)) return true;
      worklist.push(child);
    }
  }
  return false;
}

function hasSerializedProviderScaffolding(markdown: string, start: number, end: number): boolean {
  if (markdown[start] !== '"') return false;
  let source = markdown.slice(start, end);
  while (source.length > 0) {
    let decoded: unknown;
    try {
      decoded = JSON.parse(normalizeSerializedJsonWhitespace(source)) as unknown;
    } catch {
      return false;
    }
    if (Array.isArray(decoded) || (decoded !== null && typeof decoded === "object")) {
      return hasSerializedProviderKey(decoded);
    }
    if (typeof decoded !== "string" || decoded.length >= source.length) return false;
    source = decoded;
  }
  return false;
}

function isFieldBoundary(markdown: string, index: number): boolean {
  const previous = markdown[index - 1];
  return previous === undefined || isWhitespace(previous) || /[[{,}\]:="'`]/.test(previous);
}

function hasLineKey(markdown: string, start: number): boolean {
  let index = start;
  while (markdown[index] === " " || markdown[index] === "\t") index += 1;
  if (/[+*-]/.test(markdown[index] ?? "") && /[ \t]/.test(markdown[index + 1] ?? "")) {
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
      /[ \t]/.test(markdown[index + 1] ?? "")
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
  const frames: Frame[] = [{ closer: markdown[start] === "{" ? "}" : "]" }];
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
      if (hasSerializedProviderScaffolding(markdown, index, quotedEnd)) return true;
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

/** Detect provider-shaped echo/result fields without treating ordinary prose as a scaffold. */
export function hasProviderScaffolding(markdown: string): boolean {
  for (let index = 0; index < markdown.length; ) {
    if ((index === 0 || /[\r\n]/.test(markdown[index - 1] ?? "")) && hasLineKey(markdown, index)) {
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
    if (quotedEnd !== undefined && hasSerializedProviderScaffolding(markdown, index, quotedEnd)) {
      return true;
    }
    index = quotedEnd ?? index + 1;
  }
  return false;
}
