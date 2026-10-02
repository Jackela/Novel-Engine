import type { EventEmitter } from "node:events";

import JSZip from "jszip";

import type {
  ArtifactChapter,
  ArtifactWriteRequest,
} from "../application/ports/artifact_gateway.js";
import {
  EPUB_READING_CSS,
  EPUB_STYLESHEET_HREF,
  EPUB_STYLESHEET_ID,
} from "./epub_reading_style.js";
import { imageReferenceText, type MarkdownBlock, markdownBlocks } from "./export_markdown_body.js";

const xmlAllowedRanges = String.raw`\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}`;
const invalidXmlCharacters = new RegExp(`[^${xmlAllowedRanges}]`, "gu");

const XML_ESCAPES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&apos;",
};

function escapeXml(value: string): string {
  return value.replace(invalidXmlCharacters, "").replace(/[&<>"']/g, (character) => {
    return XML_ESCAPES[character] ?? character;
  });
}

/** Strip characters invalid in XML 1.0 without markup escaping. */
export function xmlSafeText(value: string): string {
  return value.replace(invalidXmlCharacters, "");
}

const DEFAULT_EXPORT_LANGUAGE = "en";
const HAN = /\p{Script=Han}/gu;
const KANA = /[\u3040-\u30ff]/gu;
const HANGUL = /[\uac00-\ud7af]/gu;
const CYRILLIC = /\p{Script=Cyrillic}/gu;
const LATIN = /\p{Script=Latin}/gu;
// Fenced code (including its info string), link/image destinations, and bare
// URLs are technical noise: counting their Latin letters used to flip an
// otherwise Chinese manuscript to `en`, so they never reach the script count.
const FENCED_CODE = /```[\s\S]*?```/gu;
const LINK_OR_IMAGE = /!?\[[^\]]*\]\([^)]*\)/gu;
const BARE_URL = /https?:\/\/\S+/gu;

/**
 * Infers the book language from the snapshot content, because the export
 * source carries no project locale setting; unknown content keeps the previous
 * `en` default. Japanese prose always mixes kana with Han characters, so kana
 * outranking a fifth of the Han count selects `ja` before Han selects `zh`.
 */
export function inferContentLanguage(request: ArtifactWriteRequest): string {
  const samples = [request.projectTitle, ...request.chapters.map(chapterText)];
  const text = samples
    .join("\n")
    .replace(FENCED_CODE, "")
    .replace(LINK_OR_IMAGE, "")
    .replace(BARE_URL, "");
  const han = countMatches(text, HAN);
  const kana = countMatches(text, KANA);
  if (kana > 0 && han > 0 && kana * 5 >= han) return "ja";
  const ranked: readonly (readonly [string, number])[] = [
    ["zh", han],
    ["ko", countMatches(text, HANGUL)],
    ["ru", countMatches(text, CYRILLIC)],
    ["en", countMatches(text, LATIN)],
  ];
  const winner = ranked.reduce((best, entry) => (entry[1] > best[1] ? entry : best));
  return winner[1] === 0 ? DEFAULT_EXPORT_LANGUAGE : winner[0];
}

/** EPUB 3 requires the package modification timestamp in UTC seconds. */
export function isoUtcTimestamp(value: Date): string {
  return value.toISOString().replace(/\.\d{3}Z$/u, "Z");
}

/**
 * Renders the snapshot chapters into one EPUB 3 stream: a package document
 * with the inferred language and modification timestamp, a built-in reading
 * stylesheet, per-chapter XHTML with preserved code blocks and image
 * references, plus the EPUB 3 navigation document and the EPUB 2 NCX fallback.
 * Bytes are produced by JSZip; the caller enforces the artifact budget.
 */
export function epubStream(request: ArtifactWriteRequest): EventEmitter {
  const zip = new JSZip();
  const language = inferContentLanguage(request);
  const chapterFiles = request.chapters.map(
    (_chapter, index) => `chapter-${String(index + 1).padStart(3, "0")}.xhtml`,
  );
  zip.file("mimetype", "application/epub+zip", { compression: "STORE" });
  zip.file(
    "META-INF/container.xml",
    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
  );
  zip.file(`OEBPS/${EPUB_STYLESHEET_HREF}`, EPUB_READING_CSS);
  for (const [index, chapter] of request.chapters.entries()) {
    zip.file(
      `OEBPS/chapter-${String(index + 1).padStart(3, "0")}.xhtml`,
      chapterXhtml(chapter, language),
    );
  }
  zip.file(
    "OEBPS/nav.xhtml",
    navigationXhtml(request.projectTitle, request.chapters, chapterFiles),
  );
  zip.file("OEBPS/toc.ncx", tableOfContents(request.projectTitle, request.chapters, chapterFiles));
  zip.file("OEBPS/content.opf", packageDocument(request, chapterFiles, language));
  return zip.generateNodeStream({ type: "nodebuffer", compression: "DEFLATE" });
}

function chapterText(chapter: ArtifactChapter): string {
  return `${chapter.title}\n${chapter.contentMarkdown}`;
}

function countMatches(text: string, pattern: RegExp): number {
  return [...text.matchAll(pattern)].length;
}

function chapterXhtml(chapter: ArtifactChapter, language: string): string {
  const body = markdownBlocks(chapter.contentMarkdown).map(blockMarkup).join("");
  return `<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${language}" lang="${language}"><head><title>${escapeXml(chapter.title)}</title><link rel="stylesheet" type="text/css" href="${EPUB_STYLESHEET_HREF}"/></head><body><h1>${escapeXml(chapter.title)}</h1>${body}</body></html>`;
}

/**
 * Block markup for one chapter body. Fenced code becomes `<pre><code>` so its
 * text survives, and an image reference becomes a readable placeholder: the
 * snapshot export source carries markdown text only, so the pixels are not
 * embedded and remote fetching stays out of the capacity-bounded renderer.
 */
function blockMarkup(block: MarkdownBlock): string {
  if (block.kind === "code") return `<pre><code>${escapeXml(block.text)}</code></pre>`;
  if (block.kind === "image") {
    return `<p class="image-placeholder">${escapeXml(imageReferenceText(block.alt, block.source))}</p>`;
  }
  return `<p>${escapeXml(block.text)}</p>`;
}

function navigationXhtml(
  title: string,
  chapters: readonly ArtifactChapter[],
  chapterFiles: readonly string[],
): string {
  const links = chapters
    .map(
      (chapter, index) =>
        `<li><a href="${chapterFiles[index]}">${escapeXml(chapter.title)}</a></li>`,
    )
    .join("");
  return `<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>${escapeXml(title)}</title></head><body><nav epub:type="toc"><ol>${links}</ol></nav></body></html>`;
}

function tableOfContents(
  title: string,
  chapters: readonly ArtifactChapter[],
  chapterFiles: readonly string[],
): string {
  const points = chapters
    .map(
      (chapter, index) =>
        `<navPoint id="chapter-${index + 1}" playOrder="${index + 1}"><navLabel><text>${escapeXml(chapter.title)}</text></navLabel><content src="${chapterFiles[index]}"/></navPoint>`,
    )
    .join("");
  return `<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><docTitle><text>${escapeXml(title)}</text></docTitle><navMap>${points}</navMap></ncx>`;
}

function packageDocument(
  request: ArtifactWriteRequest,
  chapterFiles: readonly string[],
  language: string,
): string {
  const modified = isoUtcTimestamp(request.capturedAt ?? new Date());
  const chapterItems = chapterFiles
    .map(
      (filename, index) =>
        `<item id="chapter-${index + 1}" href="${filename}" media-type="application/xhtml+xml"/>`,
    )
    .join("");
  const spine = chapterFiles
    .map((_filename, index) => `<itemref idref="chapter-${index + 1}"/>`)
    .join("");
  return `<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">${escapeXml(request.artifactId)}</dc:identifier><dc:title>${escapeXml(request.projectTitle)}</dc:title><dc:language>${escapeXml(language)}</dc:language><meta property="dcterms:modified">${modified}</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="${EPUB_STYLESHEET_ID}" href="${EPUB_STYLESHEET_HREF}" media-type="text/css"/>${chapterItems}</manifest><spine toc="toc">${spine}</spine></package>`;
}
