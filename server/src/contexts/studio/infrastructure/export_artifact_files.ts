import { createHash, randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { link, mkdir, open, realpath, unlink } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { Document, HeadingLevel, Packer, Paragraph } from "docx";

import type {
  ArtifactChapter,
  ArtifactFileEvidence,
  ArtifactReadRequest,
  ArtifactWriteRequest,
  ExportArtifactGateway,
} from "../application/export_artifact_service.js";
import type { ExportArtifactFormat } from "../application/ports/export_store.js";
import { NotFoundError } from "../domain/exceptions.js";
import { epubBytes, plainText, xmlSafeText } from "./epub_xml.js";

const extensionByFormat: Record<ExportArtifactFormat, string> = {
  markdown: "md",
  docx: "docx",
  epub: "epub",
};

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
