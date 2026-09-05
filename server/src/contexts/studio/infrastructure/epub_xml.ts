import type { EventEmitter } from "node:events";

import JSZip from "jszip";

import type { ArtifactChapter } from "../application/export_artifact_service.js";

const xmlAllowedRanges = String.raw`\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}`;
const invalidXmlCharacters = new RegExp(`[^${xmlAllowedRanges}]`, "gu");

const XML_ESCAPES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&apos;",
};

export function escapeXml(value: string): string {
  return value.replace(invalidXmlCharacters, "").replace(/[&<>"']/g, (character) => {
    return XML_ESCAPES[character] ?? character;
  });
}

/** Strip characters invalid in XML 1.0 without markup escaping. */
export function xmlSafeText(value: string): string {
  return value.replace(invalidXmlCharacters, "");
}

export function plainText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^[#>*+-]+\s*/gm, "")
    .replace(/[*_`~]/g, "")
    .trim();
}

export function epubStream(
  title: string,
  artifactId: string,
  chapters: readonly ArtifactChapter[],
): EventEmitter {
  const zip = new JSZip();
  const chapterFiles = chapters.map(
    (_chapter, index) => `chapter-${String(index + 1).padStart(3, "0")}.xhtml`,
  );
  zip.file("mimetype", "application/epub+zip", { compression: "STORE" });
  zip.file(
    "META-INF/container.xml",
    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
  );
  for (const [index, chapter] of chapters.entries()) {
    zip.file(`OEBPS/chapter-${String(index + 1).padStart(3, "0")}.xhtml`, chapterXhtml(chapter));
  }
  zip.file("OEBPS/nav.xhtml", navigationXhtml(title, chapters, chapterFiles));
  zip.file("OEBPS/toc.ncx", tableOfContents(title, chapters, chapterFiles));
  zip.file("OEBPS/content.opf", packageDocument(title, artifactId, chapterFiles));
  return zip.generateNodeStream({ type: "nodebuffer", compression: "DEFLATE" });
}

function chapterXhtml(chapter: ArtifactChapter): string {
  const paragraphs = plainText(chapter.contentMarkdown)
    .split(/\n\s*\n/)
    .filter((paragraph) => paragraph.trim() !== "")
    .map((paragraph) => `<p>${escapeXml(paragraph.trim())}</p>`)
    .join("");
  return `<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>${escapeXml(chapter.title)}</title></head><body><h1>${escapeXml(chapter.title)}</h1>${paragraphs}</body></html>`;
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
  title: string,
  artifactId: string,
  chapterFiles: readonly string[],
): string {
  const chapterItems = chapterFiles
    .map(
      (filename, index) =>
        `<item id="chapter-${index + 1}" href="${filename}" media-type="application/xhtml+xml"/>`,
    )
    .join("");
  const spine = chapterFiles
    .map((_filename, index) => `<itemref idref="chapter-${index + 1}"/>`)
    .join("");
  return `<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">${escapeXml(artifactId)}</dc:identifier><dc:title>${escapeXml(title)}</dc:title><dc:language>en</dc:language></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>${chapterItems}</manifest><spine toc="toc">${spine}</spine></package>`;
}
