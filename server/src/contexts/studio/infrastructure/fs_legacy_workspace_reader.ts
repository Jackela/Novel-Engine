import { createHash } from "node:crypto";
import { basename, dirname, isAbsolute, join, win32 } from "node:path";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  LegacyWorkspace,
  LegacyWorkspaceReader,
} from "../application/ports/legacy_workspace_reader.js";
import { LEGACY_IMPORT_LIMITS } from "../application/ports/legacy_workspace_reader.js";
import { NotFoundError } from "../domain/exceptions.js";
import {
  assertCapacity,
  assertDirectoryState,
  assertOptionalDirectoryState,
  captureDirectory,
  captureOptionalDirectory,
  type DirectoryIdentity,
  openCapturedDirectory,
  readBoundedFile,
} from "./legacy_workspace_fs_guard.js";

const STORY_ERROR = "Legacy workspace must contain story.yaml.";
const SOURCE_ERROR = "Legacy workspace source must be a real directory.";
const CHAPTER_ERROR = "Legacy workspace chapters must be regular files.";
const WEB_SOURCE_ERROR = "Web imports must name a workspace directory under data/imports.";
const CHAPTER_FILENAME = /^chapter-.*\.md$/;

interface RawFile {
  readonly relativePath: string;
  readonly contents: Buffer;
}

interface ReadChapter extends RawFile {
  readonly filename: string;
  readonly title: string;
}

interface FsLegacyWorkspaceReaderHooks {
  readonly afterFileOpen?: (path: string) => void | Promise<void>;
  readonly beforeFinalDirectoryValidation?: (source: string) => void | Promise<void>;
}

/** Local adapter that pins accepted files and bounds every read and scan. */
export class FsLegacyWorkspaceReader implements LegacyWorkspaceReader {
  constructor(private readonly hooks: FsLegacyWorkspaceReaderHooks = {}) {}

  async read(source: string): Promise<LegacyWorkspace> {
    const directory = await captureDirectory(
      source,
      (missing) => new InvalidOperationError(missing ? STORY_ERROR : SOURCE_ERROR),
    );
    return this.readWorkspace(directory);
  }

  async readConfinedLegacyWorkspace(
    dataDirectory: string,
    source: string,
  ): Promise<LegacyWorkspace> {
    assertConfinedSourceName(source);
    const fail = () =>
      new NotFoundError(`Import workspace not found under data/imports: ${source}.`);
    const root = await captureDirectory(join(dataDirectory, "imports"), fail);
    const directory = await captureDirectory(join(root.path, source), fail);
    if (dirname(directory.path) !== root.path) throw fail();
    return this.readWorkspace(directory);
  }

  private async readWorkspace(source: DirectoryIdentity): Promise<LegacyWorkspace> {
    const budget = { total: 0 };
    const story: RawFile = {
      relativePath: "story.yaml",
      contents: await readBoundedFile(
        source,
        "story.yaml",
        "story_bytes",
        STORY_ERROR,
        budget,
        this.hooks.afterFileOpen,
      ),
    };
    const manuscript = await captureOptionalDirectory(source, "manuscript");
    const chapterDirectory =
      manuscript === null ? null : await captureOptionalDirectory(manuscript, "chapters");
    const chapters =
      chapterDirectory === null ? [] : await this.readChapters(chapterDirectory, budget);
    await this.hooks.beforeFinalDirectoryValidation?.(source.path);
    await assertDirectoryState(source);
    await assertOptionalDirectoryState(source, "manuscript", manuscript);
    if (manuscript !== null) {
      await assertOptionalDirectoryState(manuscript, "chapters", chapterDirectory);
    }
    return {
      source: source.path,
      sourceHash: workspaceHash([story, ...chapters]),
      title: legacyScalar(story.contents, "title") ?? basename(source.path),
      description: legacyScalar(story.contents, "premise") ?? "",
      chapters: chapters.map(({ filename, contents, title }) => ({
        filename,
        title,
        contentMarkdown: contents.toString("utf8"),
        bytes: contents.length,
      })),
    };
  }

  private async readChapters(
    directory: DirectoryIdentity,
    budget: { total: number },
  ): Promise<ReadChapter[]> {
    const names: string[] = [];
    let entries = 0;
    const iterator = await openCapturedDirectory(directory);
    for await (const entry of iterator) {
      assertCapacity("directory_entries", LEGACY_IMPORT_LIMITS.directoryEntries, ++entries);
      if (!CHAPTER_FILENAME.test(entry.name)) continue;
      names.push(entry.name);
      assertCapacity("chapter_count", LEGACY_IMPORT_LIMITS.chapterCount, names.length);
    }
    names.sort(lexicalCompare);
    const chapters: ReadChapter[] = [];
    for (const [index, filename] of names.entries()) {
      const contents = await readBoundedFile(
        directory,
        filename,
        "chapter_bytes",
        CHAPTER_ERROR,
        budget,
        this.hooks.afterFileOpen,
      );
      chapters.push({
        filename,
        title: chapterTitle(contents, filename, index + 1),
        relativePath: `manuscript/chapters/${filename}`,
        contents,
      });
    }
    return chapters;
  }
}

/**
 * A chapter's display title derived from the source, deterministically:
 * the first non-empty line when it is an ATX heading; otherwise the filename
 * stem, where `chapter-<number>` normalizes to `Chapter <number>` and any
 * other stem loses its `chapter-` prefix and reads its separator runs as
 * spaces; `Chapter <position>` remains the last resort when the filename
 * carries no words (for example `chapter-.md`).
 */
function chapterTitle(contents: Buffer, filename: string, position: number): string {
  const text = contents.toString("utf8").replace(/^\uFEFF/, "");
  const firstLine = text.split(/\r?\n/).find((line) => line.trim() !== "");
  if (firstLine !== undefined) {
    const heading = /^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/.exec(firstLine);
    const headingText = heading?.[1]?.trim();
    if (headingText !== undefined && headingText !== "") return headingText;
  }
  const stem = filename.replace(/\.md$/i, "");
  const numbered = /^chapter[-_ ]?(\d+)$/i.exec(stem);
  if (numbered !== null) return `Chapter ${Number(numbered[1])}`;
  const words = stem
    .replace(/^chapter[-_ ]?/i, "")
    .replace(/[-_]+/g, " ")
    .trim();
  return words === "" ? `Chapter ${position}` : words;
}

/**
 * The workspace's location-independent identity: one SHA-256 digest over the
 * sorted relative file paths (`story.yaml`, `manuscript/chapters/<file>`) and
 * their exact bytes. The absolute source path and the directory name are
 * deliberately excluded, so an unchanged workspace that is moved or renamed
 * keeps the same hash and a repeated import returns the existing project
 * instead of duplicating it; any changed chapter byte, or an added or removed
 * chapter, changes the hash and is imported as a new workspace identity.
 */
function workspaceHash(files: readonly RawFile[]): string {
  const digest = createHash("sha256");
  for (const file of [...files].sort((left, right) =>
    lexicalCompare(left.relativePath, right.relativePath),
  )) {
    digest.update(file.relativePath, "utf8");
    digest.update(file.contents);
  }
  return digest.digest("hex");
}

function legacyScalar(contents: Buffer, key: "title" | "premise"): string | undefined {
  const prefix = `${key}:`;
  const lines = contents.toString("utf8").split(/\r?\n/);
  for (const [index, line] of lines.entries()) {
    if (!line.startsWith(prefix)) continue;
    const value = stripYamlComment(line.slice(prefix.length).trim());
    if (value === "") return undefined;
    if (value.startsWith("|") || value.startsWith(">")) {
      const block = blockScalarBody(lines.slice(index + 1), value.startsWith(">"));
      return block === "" ? undefined : block;
    }
    return unquoteYamlScalar(value);
  }
  return undefined;
}

function stripYamlComment(value: string): string {
  const quote = value[0];
  if (quote === '"' || quote === "'") {
    const closing = value.indexOf(quote, 1);
    return closing > 0 ? value.slice(0, closing + 1) : value;
  }
  const hash = value.indexOf(" #");
  return hash >= 0 ? value.slice(0, hash).trimEnd() : value;
}

function unquoteYamlScalar(value: string): string {
  const quote = value[0];
  return (quote === '"' || quote === "'") && value.length >= 2 && value.at(-1) === quote
    ? value.slice(1, -1)
    : value;
}

function blockScalarBody(lines: readonly string[], folded: boolean): string {
  const body: string[] = [];
  for (const line of lines) {
    if (line.trim() === "") continue;
    if (!line.startsWith(" ") && !line.startsWith("\t")) break;
    body.push(line.trim());
  }
  return (folded ? body.join(" ") : body.join("\n")).trim();
}

function lexicalCompare(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function assertConfinedSourceName(source: string): void {
  if (
    source.trim() === "" ||
    source === "." ||
    source === ".." ||
    source.includes("/") ||
    source.includes("\\") ||
    source.includes("\0") ||
    isAbsolute(source) ||
    win32.isAbsolute(source)
  ) {
    throw new InvalidOperationError(WEB_SOURCE_ERROR);
  }
}
