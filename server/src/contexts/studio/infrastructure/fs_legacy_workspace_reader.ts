import { createHash } from "node:crypto";
import { lstatSync, readdirSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, isAbsolute, join, win32 } from "node:path";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  LegacyWorkspace,
  LegacyWorkspaceReader,
} from "../application/ports/legacy_workspace_reader.js";
import { NotFoundError } from "../domain/exceptions.js";

const STORY_ERROR = "Legacy workspace must contain story.yaml.";
const SOURCE_ERROR = "Legacy workspace source must be a real directory.";
const SYMLINK_ERROR = "Legacy workspace must not contain symbolic links.";
const CHAPTER_ERROR = "Legacy workspace chapters must be regular files.";
const WEB_SOURCE_ERROR = "Web imports must name a workspace directory under data/imports.";
const IMPORT_NOT_FOUND_ERROR = "Import workspace not found under data/imports.";
const CHAPTER_FILENAME = /^chapter-.*\.md$/;

interface RawFile {
  readonly relativePath: string;
  readonly contents: Buffer;
}

interface ReadChapter extends RawFile {
  readonly filename: string;
}

/**
 * Local filesystem adapter for CLI and service use. It reads only the legacy
 * metadata file and immediate chapter files; it never traverses source links.
 */
export class FsLegacyWorkspaceReader implements LegacyWorkspaceReader {
  read(source: string): LegacyWorkspace {
    const canonicalSource = canonicalDirectory(source);
    return readWorkspace(canonicalSource);
  }

  readConfinedLegacyWorkspace(dataDirectory: string, source: string): LegacyWorkspace {
    assertConfinedSourceName(source);
    const importRoot = canonicalConfinedImportRoot(dataDirectory);
    const canonicalSource = canonicalConfinedSource(importRoot, source);
    return readWorkspace(canonicalSource);
  }
}

function readWorkspace(canonicalSource: string): LegacyWorkspace {
  const story = readStory(canonicalSource);
  const chapters = readChapters(canonicalSource);

  return {
    source: canonicalSource,
    sourceHash: workspaceHash(canonicalSource, [story, ...chapters]),
    title: legacyScalar(story.contents, "title") ?? basename(canonicalSource),
    description: legacyScalar(story.contents, "premise") ?? "",
    chapters: chapters.map((chapter) => ({
      filename: chapter.filename,
      contentMarkdown: chapter.contents.toString("utf8"),
      bytes: chapter.contents.length,
    })),
  };
}

function canonicalConfinedImportRoot(dataDirectory: string): string {
  return canonicalConfinedDirectory(join(dataDirectory, "imports"));
}

function canonicalConfinedSource(importRoot: string, source: string): string {
  const candidate = join(importRoot, source);
  const canonicalSource = canonicalConfinedDirectory(candidate);
  if (dirname(canonicalSource) !== importRoot) {
    throw new NotFoundError(IMPORT_NOT_FOUND_ERROR);
  }
  return canonicalSource;
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

function canonicalConfinedDirectory(path: string): string {
  const stat = lstatOrNull(path);
  if (stat === null || stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new NotFoundError(IMPORT_NOT_FOUND_ERROR);
  }
  try {
    return realpathSync(path);
  } catch (error) {
    if (isMissingPathError(error)) {
      throw new NotFoundError(IMPORT_NOT_FOUND_ERROR);
    }
    throw error;
  }
}

function canonicalDirectory(source: string): string {
  const root = lstatOrNull(source);
  if (root === null) {
    // Match the established legacy structure contract for a missing source.
    throw new InvalidOperationError(STORY_ERROR);
  }
  if (root.isSymbolicLink() || !root.isDirectory()) {
    throw new InvalidOperationError(SOURCE_ERROR);
  }
  try {
    return realpathSync(source);
  } catch (error) {
    if (isMissingPathError(error)) {
      throw new InvalidOperationError(STORY_ERROR);
    }
    throw error;
  }
}

function readStory(root: string): RawFile {
  return {
    relativePath: "story.yaml",
    contents: readRegularFile(join(root, "story.yaml"), STORY_ERROR),
  };
}

function readChapters(root: string): ReadChapter[] {
  const manuscript = optionalRealDirectory(join(root, "manuscript"));
  if (manuscript === null) {
    return [];
  }
  const chapterDirectory = optionalRealDirectory(join(manuscript, "chapters"));
  if (chapterDirectory === null) {
    return [];
  }

  const chapters = readdirSync(chapterDirectory, { withFileTypes: true })
    .filter((entry) => CHAPTER_FILENAME.test(entry.name))
    .map((entry) => {
      const path = join(chapterDirectory, entry.name);
      const stat = lstatOrNull(path);
      if (stat === null || stat.isSymbolicLink()) {
        throw new InvalidOperationError(SYMLINK_ERROR);
      }
      if (!stat.isFile()) {
        throw new InvalidOperationError(CHAPTER_ERROR);
      }
      return {
        filename: entry.name,
        relativePath: `manuscript/chapters/${entry.name}`,
        contents: readFileSync(path),
      };
    });

  return chapters.sort((left, right) => lexicalCompare(left.filename, right.filename));
}

function optionalRealDirectory(path: string): string | null {
  const stat = lstatOrNull(path);
  if (stat === null) {
    return null;
  }
  if (stat.isSymbolicLink()) {
    throw new InvalidOperationError(SYMLINK_ERROR);
  }
  if (!stat.isDirectory()) {
    throw new InvalidOperationError(CHAPTER_ERROR);
  }
  return path;
}

function readRegularFile(path: string, message: string): Buffer {
  const stat = lstatOrNull(path);
  if (stat === null || stat.isSymbolicLink() || !stat.isFile()) {
    throw new InvalidOperationError(message);
  }
  return readFileSync(path);
}

function workspaceHash(root: string, files: readonly RawFile[]): string {
  const digest = createHash("sha256");
  digest.update(root, "utf8");
  for (const file of [...files].sort((left, right) =>
    lexicalCompare(left.relativePath, right.relativePath),
  )) {
    digest.update(file.relativePath, "utf8");
    digest.update(file.contents);
  }
  return digest.digest("hex");
}

/**
 * Read one scalar `key` from the workspace's story.yaml the way the Python
 * authority's yaml.safe_load would present it: surrounding quotes stripped,
 * unquoted trailing comments removed, and indented block scalars folded
 * (`>` joins with spaces, `|` keeps line breaks).
 */
function legacyScalar(contents: Buffer, key: "title" | "premise"): string | undefined {
  const prefix = `${key}:`;
  const lines = contents.toString("utf8").split(/\r?\n/);
  for (const [index, line] of lines.entries()) {
    if (!line.startsWith(prefix)) {
      continue;
    }
    const value = stripYamlComment(line.slice(prefix.length).trim());
    if (value === "") {
      return undefined;
    }
    if (value.startsWith("|") || value.startsWith(">")) {
      const block = blockScalarBody(lines.slice(index + 1), value.startsWith(">"));
      return block === "" ? undefined : block;
    }
    return unquoteYamlScalar(value);
  }
  return undefined;
}

/** Drop a trailing `# comment`; inside quotes the hash is literal content. */
function stripYamlComment(value: string): string {
  const quote = value[0];
  if (quote === '"' || quote === "'") {
    const closing = value.indexOf(quote, 1);
    return closing > 0 ? value.slice(0, closing + 1) : value;
  }
  const hash = value.indexOf(" #");
  return hash >= 0 ? value.slice(0, hash).trimEnd() : value;
}

/** Remove one layer of matching surrounding quotes. */
function unquoteYamlScalar(value: string): string {
  const quote = value[0];
  if ((quote === '"' || quote === "'") && value.length >= 2 && value[value.length - 1] === quote) {
    return value.slice(1, -1);
  }
  return value;
}

/** Fold the indented continuation lines of a block scalar. */
function blockScalarBody(lines: readonly string[], folded: boolean): string {
  const body: string[] = [];
  for (const line of lines) {
    if (line.trim() === "") {
      continue;
    }
    if (!line.startsWith(" ") && !line.startsWith("\t")) {
      break;
    }
    body.push(line.trim());
  }
  return (folded ? body.join(" ") : body.join("\n")).trim();
}

function lexicalCompare(left: string, right: string): number {
  if (left < right) {
    return -1;
  }
  return left > right ? 1 : 0;
}

function lstatOrNull(path: string) {
  try {
    return lstatSync(path);
  } catch (error) {
    if (isMissingPathError(error)) {
      return null;
    }
    throw error;
  }
}

function isMissingPathError(error: unknown): error is NodeJS.ErrnoException {
  return typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT";
}
