import { createHash, randomUUID } from "node:crypto";
import {
  lstat,
  mkdir,
  readFile,
  realpath,
  rename,
  stat,
  unlink,
  writeFile,
} from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { Document, HeadingLevel, Packer, Paragraph } from "docx";
import JSZip from "jszip";

import type {
  ArtifactChapter,
  ArtifactFileEvidence,
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

/** Filesystem implementation of atomic rendering and confined artifact lookup. */
export class FilesystemExportArtifactGateway implements ExportArtifactGateway {
  constructor(private readonly dataDirectory: string) {}

  async writeSnapshotArtifact(request: ArtifactWriteRequest): Promise<ArtifactFileEvidence> {
    assertSafePart(request.projectId);
    assertSafePart(request.artifactId);
    const dataRoot = resolve(this.dataDirectory);
    const exportsRoot = resolve(dataRoot, "exports");
    const directory = resolve(exportsRoot, request.projectId);
    if (!isDescendant(exportsRoot, directory)) {
      throw new Error("Export directory is outside the configured root.");
    }
    await mkdir(directory, { recursive: true });
    const realDataRoot = await realpath(dataRoot);
    const realExportsRoot = await realpath(exportsRoot);
    const realDirectory = await realpath(directory);
    if (
      !isDescendant(realDataRoot, realExportsRoot) ||
      !isDescendant(realExportsRoot, realDirectory)
    ) {
      throw new Error("Export directory escapes the configured root.");
    }
    const filename = `${request.artifactId}.${extensionByFormat[request.format]}`;
    const target = resolve(realDirectory, filename);
    if (!isDescendant(realExportsRoot, target)) {
      throw new Error("Export target is outside the configured root.");
    }
    const temporary = resolve(realDirectory, `.${filename}.${randomUUID()}.tmp`);
    const contents = await serializeArtifact(request);
    let replaced = false;
    try {
      await writeFile(temporary, contents, { flag: "wx" });
      await rename(temporary, target);
      replaced = true;
      const relativePath = ["exports", request.projectId, filename].join("/");
      const finalPath = await this.resolveArtifactFile(relativePath);
      const finalContents = await readFile(finalPath);
      const finalStat = await stat(finalPath);
      return {
        relativePath,
        sizeBytes: finalStat.size,
        checksumSha256: createHash("sha256").update(finalContents).digest("hex"),
      };
    } finally {
      if (!replaced) {
        await unlinkIfPresent(temporary);
      }
    }
  }

  async resolveArtifactFile(relativePath: string): Promise<string> {
    try {
      const dataRoot = resolve(this.dataDirectory);
      const exportsRoot = resolve(dataRoot, "exports");
      const candidate = resolveStoredPath(dataRoot, exportsRoot, relativePath);
      const realDataRoot = await realpath(dataRoot);
      const realExportsRoot = await realpath(exportsRoot);
      const entry = await lstat(candidate);
      if (entry.isSymbolicLink() || !entry.isFile()) {
        throw new Error("Export entry is not a regular file.");
      }
      const realCandidate = await realpath(candidate);
      if (
        !isDescendant(realDataRoot, realExportsRoot) ||
        !isDescendant(realExportsRoot, realCandidate) ||
        !(await stat(realCandidate)).isFile()
      ) {
        throw new Error("Export entry escapes the configured root.");
      }
      return realCandidate;
    } catch {
      throw new NotFoundError("Export file not found.");
    }
  }
}

function resolveStoredPath(dataRoot: string, exportsRoot: string, relativePath: string): string {
  const parts = relativePath.split("/");
  if (
    relativePath === "" ||
    isAbsolute(relativePath) ||
    relativePath.includes("\\") ||
    parts[0] !== "exports" ||
    parts.some((part) => part === "" || part === "." || part === "..")
  ) {
    throw new Error("Stored export path is invalid.");
  }
  const candidate = resolve(dataRoot, ...parts);
  if (!isDescendant(dataRoot, candidate) || !isDescendant(exportsRoot, candidate)) {
    throw new Error("Stored export path is outside the configured root.");
  }
  return candidate;
}

function assertSafePart(value: string): void {
  if (
    value === "" ||
    value === "." ||
    value === ".." ||
    value.includes("/") ||
    value.includes("\\")
  ) {
    throw new Error("Export identifier is invalid.");
  }
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}

async function unlinkIfPresent(path: string): Promise<void> {
  try {
    await unlink(path);
  } catch (error) {
    if (!(error instanceof Error) || !hasCode(error, "ENOENT")) {
      throw error;
    }
  }
}

function hasCode(error: Error, code: string): error is Error & { code: string } {
  return "code" in error && error.code === code;
}

async function serializeArtifact(request: ArtifactWriteRequest): Promise<Buffer> {
  if (request.format === "markdown") {
    return Buffer.from(markdownText(request.projectTitle, request.chapters), "utf8");
  }
  if (request.format === "docx") {
    return docxBytes(request.projectTitle, request.chapters);
  }
  return epubBytes(request.projectTitle, request.artifactId, request.chapters);
}

function markdownText(title: string, chapters: readonly ArtifactChapter[]): string {
  return `${[`# ${title}`, ...chapters.map((chapter) => chapter.contentMarkdown.trim())]
    .join("\n\n")
    .trim()}\n`;
}

async function docxBytes(title: string, chapters: readonly ArtifactChapter[]): Promise<Buffer> {
  const children: Paragraph[] = [new Paragraph({ text: title, heading: HeadingLevel.TITLE })];
  for (const chapter of chapters) {
    children.push(new Paragraph({ text: chapter.title, heading: HeadingLevel.HEADING_1 }));
    for (const paragraph of plainText(chapter.contentMarkdown).split(/\n\s*\n/)) {
      if (paragraph.trim() !== "") {
        children.push(new Paragraph({ text: paragraph.trim() }));
      }
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
    const filename = chapterFiles[index];
    if (filename === undefined) {
      throw new Error("EPUB chapter name is unavailable.");
    }
    zip.file(`OEBPS/${filename}`, chapterXhtml(chapter));
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

function escapeXml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
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
