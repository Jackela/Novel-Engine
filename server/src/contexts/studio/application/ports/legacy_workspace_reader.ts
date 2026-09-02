/** One chapter discovered in a legacy workspace without changing its source. */
export interface LegacyWorkspaceChapter {
  readonly filename: string;
  readonly contentMarkdown: string;
  readonly bytes: number;
}

/**
 * Canonical, principal-independent identity and content of a legacy workspace.
 * Principal scoping belongs to the import application service, not this reader.
 */
export interface LegacyWorkspace {
  readonly source: string;
  readonly sourceHash: string;
  readonly title: string;
  readonly description: string;
  readonly chapters: readonly LegacyWorkspaceChapter[];
}

export const LEGACY_IMPORT_LIMITS = Object.freeze({
  storyBytes: 262_144,
  chapterBytes: 4_194_304,
  workspaceBytes: 67_108_864,
  chapterCount: 2_000,
  directoryEntries: 4_096,
});

/**
 * Read-only boundary for legacy workspace inspection. The CLI may pass an
 * explicit local path; the web surface applies its own data/imports confinement.
 */
export interface LegacyWorkspaceReader {
  /** Read an explicit local path supplied by the trusted local CLI. */
  read(source: string): Promise<LegacyWorkspace>;
  /**
   * Read one direct workspace name below the application-owned `data/imports`
   * root. The web preview passes its untrusted source name here; this boundary
   * rejects paths and links before inspecting workspace content.
   */
  readConfinedLegacyWorkspace(dataDirectory: string, source: string): Promise<LegacyWorkspace>;
}
