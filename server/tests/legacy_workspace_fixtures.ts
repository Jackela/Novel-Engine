import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export interface LegacyChapterInput {
  filename: string;
  content: string;
}

export interface LegacyWorkspaceInput {
  /** When absent the story.yaml file omits the key (title falls back). */
  title?: string;
  premise?: string;
  chapters: LegacyChapterInput[];
}

/**
 * Write a legacy workspace under `root`: `story.yaml` plus
 * `manuscript/chapters/chapter-*.md` files, the pre-import data layout.
 */
export function makeLegacyWorkspace(root: string, input: LegacyWorkspaceInput): string {
  const chaptersDir = join(root, "manuscript", "chapters");
  mkdirSync(chaptersDir, { recursive: true });
  const lines: string[] = [];
  if (input.title !== undefined) {
    lines.push(`title: ${input.title}`);
  }
  if (input.premise !== undefined) {
    lines.push(`premise: ${input.premise}`);
  }
  writeFileSync(join(root, "story.yaml"), `${lines.join("\n")}\n`, "utf8");
  for (const chapter of input.chapters) {
    writeFileSync(join(chaptersDir, chapter.filename), chapter.content, "utf8");
  }
  return root;
}

/**
 * Content digest over every regular file under `root` (relative path plus
 * bytes): the read-only proof that an import left the source untouched.
 */
export function directoryFingerprint(root: string): string {
  const digest = createHash("sha256");
  const walk = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true })
      .flatMap((entry) => {
        const full = join(dir, entry.name);
        return entry.isDirectory() ? walk(full) : [full];
      })
      .sort();
  for (const file of walk(root)) {
    digest.update(file.slice(root.length), "utf8");
    digest.update(readFileSync(file));
  }
  return digest.digest("hex");
}
