/**
 * Markdown body parsing shared by the DOCX and EPUB renderers. Chapter
 * markdown is authored with a leading title line, so both formats must be able
 * to drop that repeated line, and the EPUB writer needs structured blocks so
 * fenced code blocks and image references reach the reader instead of being
 * deleted. Nothing here renders markup: callers own their own escaping.
 */

/** One chapter-body block after fenced code blocks are extracted. */
export type MarkdownBlock =
  | { readonly kind: "paragraph"; readonly text: string }
  | { readonly kind: "code"; readonly text: string }
  | { readonly kind: "image"; readonly alt: string; readonly source: string };

const IMAGE_PATTERN = "!\\[([^\\]]*)\\]\\(([^)\\s]+)\\)";
const INLINE_IMAGE = new RegExp(IMAGE_PATTERN, "gu");
const STANDALONE_IMAGE = new RegExp(`^${IMAGE_PATTERN}$`, "u");
const PLAIN_LINK = /\[([^\]]+)\]\([^)]*\)/gu;
const LINE_MARKER = /^[#>*+-]+\s*/gmu;
const INLINE_EMPHASIS = /[*_`~]/gu;
const FENCED_CODE = /^```[^\n]*\r?\n([\s\S]*?)^```[ \t]*$/gmu;
const TRAILING_NEWLINE = /\r?\n$/u;

/**
 * Prose rendering for the DOCX body: markdown markers are stripped and fenced
 * code blocks, image references, and link targets are dropped because the
 * manuscript keeps running text only. Invalid XML characters are the caller's
 * responsibility (xmlSafeText).
 */
export function plainText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(PLAIN_LINK, "$1")
    .replace(LINE_MARKER, "")
    .replace(INLINE_EMPHASIS, "")
    .trim();
}

/**
 * Drops the leading markdown line when it merely repeats the chapter title,
 * which is how the chapter heading used to reappear as the first body
 * paragraph. A different first line is left untouched and only loses its `#`
 * markers, so no authored prose can disappear from the export.
 */
export function stripRepeatedTitleLine(title: string, markdown: string): string {
  const expected = normalizeTitle(title);
  if (expected === "") return markdown;
  const lines = markdown.split("\n");
  const firstContentLine = lines.findIndex((line) => line.trim() !== "");
  if (firstContentLine < 0) return markdown;
  const candidate = normalizeTitle(
    (lines[firstContentLine] ?? "").replace(/^#{1,6}\s*/u, "").replace(/[*_`~]/gu, ""),
  );
  if (candidate === "" || candidate !== expected) return markdown;
  return lines.slice(firstContentLine + 1).join("\n");
}

/**
 * Splits a chapter body into paragraph, code, and image blocks. Blank lines
 * separate paragraphs; fenced code blocks keep their content verbatim (fences
 * alone are dropped) and a paragraph that is exactly one image becomes an
 * image block so the reader still sees the alt text and source reference.
 */
export function markdownBlocks(markdown: string): readonly MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  let cursor = 0;
  for (const match of markdown.matchAll(FENCED_CODE)) {
    const start = match.index ?? 0;
    appendProseBlocks(blocks, markdown.slice(cursor, start));
    blocks.push({ kind: "code", text: (match[1] ?? "").replace(TRAILING_NEWLINE, "") });
    cursor = start + match[0].length;
  }
  appendProseBlocks(blocks, markdown.slice(cursor));
  return blocks;
}

/** Reader-visible stand-in for an image whose pixels the export does not carry. */
export function imageReferenceText(alt: string, source: string): string {
  const label = alt.trim() === "" ? "[image]" : `[image: ${alt.trim()}]`;
  return `${label} ${source}`;
}

function appendProseBlocks(blocks: MarkdownBlock[], prose: string): void {
  for (const raw of prose.split(/\n\s*\n/u)) {
    const trimmed = raw.trim();
    if (trimmed === "") continue;
    const standalone = STANDALONE_IMAGE.exec(trimmed);
    if (standalone !== null) {
      blocks.push({ kind: "image", alt: standalone[1] ?? "", source: standalone[2] ?? "" });
      continue;
    }
    const text = proseText(trimmed);
    if (text !== "") blocks.push({ kind: "paragraph", text });
  }
}

function proseText(raw: string): string {
  return raw
    .replace(INLINE_IMAGE, (_match, alt: string, source: string) => imageReferenceText(alt, source))
    .replace(PLAIN_LINK, "$1")
    .replace(LINE_MARKER, "")
    .replace(INLINE_EMPHASIS, "")
    .trim();
}

function normalizeTitle(value: string): string {
  return value.replace(/\s+/gu, " ").trim();
}
