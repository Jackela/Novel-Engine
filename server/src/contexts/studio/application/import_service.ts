import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { dumpJson } from "./payloads.js";
import type { LegacyWorkspace, LegacyWorkspaceReader } from "./ports/legacy_workspace_reader.js";
import { type ProjectRecord, type StudioStore, scopeForPrincipal } from "./ports/studio_store.js";

/** Imported projects keep the authoring-core default settings (Python parity). */
const IMPORT_SETTINGS_JSON = dumpJson({ provider: "mock" });

export interface LegacyImportResult extends Record<string, unknown> {
  readonly project_id: string;
  readonly title: string;
  readonly description: string;
  readonly import_hash: string;
  readonly chapter_count: number;
  readonly created: boolean;
}

/**
 * Read-only, idempotent import of a legacy file workspace. The workspace
 * layout (story.yaml plus manuscript/chapters/chapter-*.md) is read through
 * the LegacyWorkspaceReader port; nothing here ever writes to the source.
 */
export class ImportService {
  private readonly store: StudioStore;
  private readonly reader: LegacyWorkspaceReader;
  private readonly now: () => Date;

  constructor(
    store: StudioStore,
    reader: LegacyWorkspaceReader,
    now: () => Date = () => new Date(),
  ) {
    this.store = store;
    this.reader = reader;
    this.now = now;
  }

  /**
   * Web preview: the untrusted source name is confined to one real directory
   * below the application-owned data/imports root by the reader before any
   * workspace content is inspected. Never writes.
   */
  async previewConfinedLegacyWorkspace(
    dataDirectory: string,
    source: string,
  ): Promise<Record<string, unknown>> {
    const workspace = await this.reader.readConfinedLegacyWorkspace(dataDirectory, source);
    return legacyPreviewPayload(workspace);
  }

  /**
   * Import the workspace for this principal, or return the project an earlier
   * import of the same source hash already created in this principal's scope.
   */
  async importLegacyWorkspace(principal: Principal, source: string): Promise<LegacyImportResult> {
    const workspace = await this.reader.read(source);
    const scope = scopeForPrincipal(principal);
    const existing = this.store.findProjectByImportHash(scope, workspace.sourceHash);
    if (existing !== null) {
      return legacyImportResult(existing, workspace, false);
    }
    const title = workspace.title.trim();
    if (title === "") {
      throw new InvalidOperationError("Project title is required.");
    }
    const created = this.store.addImportedProject(scope, {
      title,
      description: workspace.description.trim(),
      settingsJson: IMPORT_SETTINGS_JSON,
      importHash: workspace.sourceHash,
      chapters: workspace.chapters.map((chapter) => ({
        contentMarkdown: chapter.contentMarkdown,
        metadataJson: dumpJson({ legacy_filename: chapter.filename }),
      })),
      now: this.now(),
    });
    return legacyImportResult(created.project, workspace, true);
  }
}

function legacyImportResult(
  project: ProjectRecord,
  workspace: LegacyWorkspace,
  created: boolean,
): LegacyImportResult {
  return {
    project_id: project.id,
    title: project.title,
    description: project.description,
    import_hash: project.importHash ?? workspace.sourceHash,
    chapter_count: workspace.chapters.length,
    created,
  };
}

/** The fixed summary of what an import would create (Python preview parity). */
function legacyPreviewPayload(workspace: LegacyWorkspace): Record<string, unknown> {
  return {
    source: workspace.source,
    source_hash: workspace.sourceHash,
    title: workspace.title,
    description: workspace.description,
    chapter_count: workspace.chapters.length,
    chapters: workspace.chapters.map((chapter) => ({
      filename: chapter.filename,
      bytes: chapter.bytes,
    })),
  };
}
