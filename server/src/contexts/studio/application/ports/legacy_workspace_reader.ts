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

/**
 * Read-only boundary for legacy workspace inspection. The CLI may pass an
 * explicit local path; the web surface applies its own data/imports confinement.
 */
export interface LegacyWorkspaceReader {
  read(source: string): LegacyWorkspace;
}
