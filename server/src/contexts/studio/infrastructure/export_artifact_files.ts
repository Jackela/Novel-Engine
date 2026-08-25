import { createHash, randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { link, mkdir, open, realpath, unlink } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { Document, HeadingLevel, Packer, Paragraph } from "docx";
import JSZip from "jszip";

import type {
  ArtifactChapter,
  ArtifactFileEvidence,
  ArtifactReadRequest,
  ArtifactWriteRequest,
  ExportArtifactGateway,
} from "../application/export_artifact_service.js";
import type { ExportArtifactFormat } from "../application/ports/export_store.js";
import { NotFoundError } from "../domain/exceptions.js";

const extensionByFormat: Record<ExportArtifactFormat, string> = {
  markdown: "md",
  docx: "docx",
  epub: "epub",
};
const xmlAllowedRanges = String.raw`\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}`;
const invalidXmlCharacters = new RegExp(`[^${xmlAllowedRanges}]`, "gu");

// Filesystem implementation of atomic rendering and confined artifact lookup.
export class FilesystemExportArtifactGateway implements ExportArtifactGateway {
  constructor(private readonly dataDirectory: string) {}

  async writeSnapshotArtifact(request: ArtifactWriteRequest): Promise<ArtifactFileEvidence> {
    const names = artifactNames(request.projectId, request.artifactId, request.format);
    const contents = await serializeArtifact(request);
    const directory = await artifactDirectory(this.dataDirectory, request.projectId, true);
    const target = resolve(directory, names.filename);
    const temporary = resolve(directory, `.${request.artifactId}.${randomUUID()}.tmp`);
    return publishArtifact(temporary, target, contents, names.relativePath);
  }

  async readArtifactBytes(request: ArtifactReadRequest): Promise<Buffer> {
    try {
      const names = artifactNames(request.projectId, request.artifactId, request.format);
      if (request.relativePath !== names.relativePath)
        throw new Error("Stored export path is invalid.");
      const directory = await artifactDirectory(this.dataDirectory, request.projectId, false);
      return await readVerifiedArtifact(resolve(directory, names.filename), request);
    } catch {
      throw new NotFoundError("Export file not found.");
    }
  }
}

async function artifactDirectory(
  dataDirectory: string,
  projectId: string,
  create: boolean,
): Promise<string> {
  assertSafePart(projectId);
  const dataRoot = resolve(dataDirectory);
  const exportsRoot = resolve(dataRoot, "exports");
  const directory = resolve(exportsRoot, projectId);
  if (!isDescendant(dataRoot, exportsRoot) || !isDescendant(exportsRoot, directory)) {
    throw new Error("Export directory is outside the configured root.");
  }
  if (create) await mkdir(directory, { recursive: true });
  const [realDataRoot, realExportsRoot, realDirectory] = await Promise.all([
    realpath(dataRoot),
    realpath(exportsRoot),
    realpath(directory),
  ]);
  if (
    !isDescendant(realDataRoot, realExportsRoot) ||
    !isDescendant(realExportsRoot, realDirectory)
  ) {
    throw new Error("Export directory escapes the configured root.");
  }
  return realDirectory;
}

function artifactNames(
  projectId: string,
  artifactId: string,
  format: ExportArtifactFormat,
): { filename: string; relativePath: string } {
  assertSafePart(projectId);
  assertSafePart(artifactId);
  const extension = extensionByFormat[format];
  if (extension === undefined) throw new Error("Export format is invalid.");
  const filename = `${artifactId}.${extension}`;
  return { filename, relativePath: `exports/${projectId}/${filename}` };
}

function assertSafePart(value: string): void {
  if (value === "" || value === "." || value === ".." || /[\\/\0]/.test(value)) {
    throw new Error("Export identifier is invalid.");
  }
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}

async function publishArtifact(
  temporary: string,
  target: string,
  contents: Buffer,
  relativePath: string,
): Promise<ArtifactFileEvidence> {
  let handle: Awaited<ReturnType<typeof open>> | undefined;
  let linked = false;
  try {
    handle = await open(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL);
    await handle.writeFile(contents);
    await handle.sync();
    const identity = await handle.stat();
    await handle.close();
    handle = undefined;
    await link(temporary, target);
    linked = true;
    await unlink(temporary);
    const checksumSha256 = createHash("sha256").update(contents).digest("hex");
    return {
      relativePath,
      sizeBytes: contents.length,
      checksumSha256,
      rollback: () => rollbackPublishedArtifact(target, contents, identity.dev, identity.ino),
    };
  } catch (error) {
    if (handle !== undefined) await ignore(handle.close());
    if (linked) await ignore(unlink(target));
    await ignore(unlink(temporary));
    throw error;
  }
}

async function readVerifiedArtifact(target: string, request: ArtifactReadRequest): Promise<Buffer> {
  // Node has no portable openat directory-fd API: parent checks precede leaf O_NOFOLLOW protection.
  const handle = await open(target, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const details = await handle.stat();
    const contents = await handle.readFile();
    if (
      !details.isFile() ||
      details.size !== request.sizeBytes ||
      contents.length !== request.sizeBytes ||
      createHash("sha256").update(contents).digest("hex") !== request.checksumSha256
    ) {
      throw new Error("Export integrity evidence does not match.");
    }
    return contents;
  } finally {
    await handle.close();
  }
}

async function rollbackPublishedArtifact(
  target: string,
  contents: Buffer,
  dev: number,
  ino: number,
): Promise<void> {
  try {
    const handle = await open(target, constants.O_RDONLY | constants.O_NOFOLLOW);
    try {
      const details = await handle.stat();
      const actual = await handle.readFile();
      if (
        !details.isFile() ||
        details.dev !== dev ||
        details.ino !== ino ||
        !actual.equals(contents)
      ) {
        return;
      }
    } finally {
      await handle.close();
    }
    await unlink(target);
  } catch {
    return;
  }
}

async function ignore(promise: Promise<unknown>): Promise<void> {
  try {
    await promise;
  } catch {
    return;
  }
}

async function serializeArtifact(request: ArtifactWriteRequest): Promise<Buffer> {
  if (request.format === "markdown")
    return Buffer.from(markdownText(request.projectTitle, request.chapters), "utf8");
  return request.format === "docx"
    ? docxBytes(request.projectTitle, request.chapters)
    : epubBytes(request.projectTitle, request.artifactId, request.chapters);
}

function markdownText(title: string, chapters: readonly ArtifactChapter[]): string {
  return `${[`# ${title}`, ...chapters.map((chapter) => chapter.contentMarkdown.trim())]
    .join("\n\n")
    .trim()}\n`;
}

async function docxBytes(title: string, chapters: readonly ArtifactChapter[]): Promise<Buffer> {
  // The docx library escapes markup itself but does not strip characters that
  // are invalid in XML 1.0; user-saved titles and prose must not corrupt
  // word/document.xml (the EPUB path gets the same treatment via escapeXml).
  const children: Paragraph[] = [
    new Paragraph({ text: xmlSafeText(title), heading: HeadingLevel.TITLE }),
  ];
  for (const chapter of chapters) {
    children.push(
      new Paragraph({ text: xmlSafeText(chapter.title), heading: HeadingLevel.HEADING_1 }),
    );
    for (const paragraph of plainText(chapter.contentMarkdown).split(/\n\s*\n/)) {
      const text = xmlSafeText(paragraph.trim());
      if (text !== "") children.push(new Paragraph({ text }));
    }
  }
  return Packer.toBuffer(new Document({ sections: [{ children }] }));
}

async function epubBytes(
  title: string,
  artifactId: string,
  chapters: readonly ArtifactChapter[],
): Promise<Buffer> {
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
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

function plainText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^[#>*+-]+\s*/gm, "")
    .replace(/[*_`~]/g, "")
    .trim();
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

/** Strip characters invalid in XML 1.0 without markup escaping. */
function xmlSafeText(value: string): string {
  return value.replace(invalidXmlCharacters, "");
}

function escapeXml(value: string): string {
  return value.replace(invalidXmlCharacters, "").replace(/[&<>"']/g, (character) => {
    const escaped: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&apos;",
    };
    return escaped[character] ?? character;
  });
}
