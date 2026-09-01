import { createHash } from "node:crypto";
import { constants } from "node:fs";
import { lstat, mkdir, open, realpath } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { Document, HeadingLevel, Packer, Paragraph } from "docx";
import { exportArtifactNames } from "../application/export_artifact_identity.js";
import type {
  ArtifactChapter,
  ArtifactFileEvidence,
  ArtifactReadRequest,
  ArtifactWriteRequest,
  ExportArtifactGateway,
} from "../application/export_artifact_service.js";
import { ExportArtifactWriteError, NotFoundError } from "../domain/exceptions.js";
import { epubBytes, plainText, xmlSafeText } from "./epub_xml.js";
import { errorCode, syncDirectory } from "./export_artifact_fs_support.js";
import { publishArtifact as publishDurableArtifact } from "./export_artifact_publication.js";
import type { ExportPublicationCleanupJournal } from "./export_publication_cleanup_journal.js";

export interface FilesystemExportArtifactGatewayOptions {
  /** Durable database authority for replaying interrupted rollback cleanup. */
  readonly cleanupJournal?: ExportPublicationCleanupJournal | undefined;
  /** Deterministic publication/temporary ids used only by collision tests. */
  readonly newId?: (() => string) | undefined;
  /** Deterministic shared-staging race seam used only by filesystem tests. */
  readonly afterStagingReady?: (() => Promise<void>) | undefined;
  /** Deterministic race seam used only by filesystem rollback tests. */
  readonly afterRollbackQuarantine?:
    | ((quarantine: string, target: string) => Promise<void>)
    | undefined;
}

// Filesystem implementation of atomic rendering and confined artifact lookup.
export class FilesystemExportArtifactGateway implements ExportArtifactGateway {
  constructor(
    private readonly dataDirectory: string,
    private readonly options: FilesystemExportArtifactGatewayOptions = {},
  ) {}

  async writeSnapshotArtifact(
    request: ArtifactWriteRequest,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<ArtifactFileEvidence> {
    const names = exportArtifactNames(request.projectId, request.artifactId, request.format);
    const contents = await serializeArtifact(request);
    try {
      const directory = await artifactDirectory(this.dataDirectory, request.projectId, true);
      const target = resolve(directory, names.filename);
      return await publishDurableArtifact({
        projectDirectory: directory,
        target,
        relativePath: names.relativePath,
        projectId: request.projectId,
        artifactId: request.artifactId,
        format: request.format,
        contents,
        reportCleanupFailure,
        newId: this.options.newId,
        afterStagingReady: this.options.afterStagingReady,
        afterRollbackQuarantine: this.options.afterRollbackQuarantine,
        cleanupJournal: this.options.cleanupJournal,
      });
    } catch (error) {
      if (isKnownWriteFailure(error)) throw new ExportArtifactWriteError();
      throw error;
    }
  }

  async readArtifactBytes(request: ArtifactReadRequest): Promise<Buffer> {
    try {
      const names = exportArtifactNames(request.projectId, request.artifactId, request.format);
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
  const dataRoot = await realpath(resolve(dataDirectory));
  const exportsRoot = await realChildDirectory(dataRoot, "exports", create);
  return realChildDirectory(exportsRoot, projectId, create);
}

async function realChildDirectory(parent: string, name: string, create: boolean): Promise<string> {
  const candidate = resolve(parent, name);
  if (!isDescendant(parent, candidate)) {
    throw new Error("Export directory is outside the configured root.");
  }
  let details: Awaited<ReturnType<typeof lstat>>;
  try {
    details = await lstat(candidate);
  } catch (error) {
    if (!create || errorCode(error) !== "ENOENT") throw error;
    try {
      await mkdir(candidate);
    } catch (mkdirError) {
      if (errorCode(mkdirError) !== "EEXIST") throw mkdirError;
    }
    details = await lstat(candidate);
  }
  if (details.isSymbolicLink() || !details.isDirectory()) {
    throw new Error("Export directory is not a real directory.");
  }
  const actual = await realpath(candidate);
  if (!isDescendant(parent, actual)) {
    throw new Error("Export directory escapes the configured root.");
  }
  // A first export may create both exports/ and its project leaf. Syncing the
  // parent before publication makes those directory entries durable before
  // SQLite can commit the artifact row.
  if (create) await syncDirectory(parent);
  return actual;
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
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

const KNOWN_WRITE_ERROR_CODES = new Set([
  "EACCES",
  "EBUSY",
  "EDQUOT",
  "EMLINK",
  "EFBIG",
  "EIO",
  "ENAMETOOLONG",
  "EMFILE",
  "ENFILE",
  "ENOENT",
  "ENOSYS",
  "ENOSPC",
  "ENOTSUP",
  "EOPNOTSUPP",
  "EPERM",
  "EROFS",
  "EXDEV",
]);

function isKnownWriteFailure(error: unknown): boolean {
  const code = errorCode(error);
  return code !== undefined && KNOWN_WRITE_ERROR_CODES.has(code);
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
