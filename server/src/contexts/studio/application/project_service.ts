import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { InvalidProjectUpdateError } from "../domain/exceptions.js";
import { InFlightOperationGuard } from "./operation_in_flight.js";
import { dumpJson, projectPayload } from "./payloads.js";
import type { ProjectArtifactCleaner } from "./ports/project_artifact_cleaner.js";
import {
  type DocumentSummaryRecord,
  type StudioStore,
  scopeForPrincipal,
} from "./ports/studio_store.js";
import { projectShellPayload, summarizeDocument } from "./project_shell_payloads.js";

/** The adjudicated new-project seed (mirrors the Python authority). */
const SEED_DOCUMENT_TITLE = "Chapter 1";
const SEED_DOCUMENT_CONTENT = "# Chapter 1\n\n";
const DEFAULT_SETTINGS = dumpJson({ provider: "mock" });

export interface ProjectServiceOptions {
  /** Shared with provider/export operations in the app composition root. */
  readonly inFlight?: InFlightOperationGuard | undefined;
  /** Optional only for persistence-focused unit harnesses. */
  readonly artifactCleaner?: ProjectArtifactCleaner | undefined;
}

export class ProjectService {
  private readonly store: StudioStore;
  private readonly now: () => Date;
  private readonly inFlight: InFlightOperationGuard;
  private readonly artifactCleaner: ProjectArtifactCleaner | undefined;

  constructor(
    store: StudioStore,
    now: () => Date = () => new Date(),
    options: ProjectServiceOptions = {},
  ) {
    this.store = store;
    this.now = now;
    this.inFlight = options.inFlight ?? new InFlightOperationGuard();
    this.artifactCleaner = options.artifactCleaner;
  }

  /** Create a project with the Chapter 1 seed and default provider settings. */
  newProject(
    principal: Principal,
    input: { title: string; description?: string | undefined },
  ): Record<string, unknown> {
    const title = input.title.trim();
    if (title === "") {
      throw new InvalidOperationError("Project title is required.");
    }
    const description = (input.description ?? "").trim();
    const scope = scopeForPrincipal(principal);
    const created = this.store.addProject(scope, {
      title,
      description,
      settingsJson: DEFAULT_SETTINGS,
      seed: {
        kind: "chapter",
        title: SEED_DOCUMENT_TITLE,
        contentMarkdown: SEED_DOCUMENT_CONTENT,
        metadataJson: dumpJson({}),
      },
      now: this.now(),
    });
    // The seeded default volume arrives from the creation transaction's own
    // structure; reading it back keeps this service persistence-neutral.
    return projectShellPayload(
      created.project,
      created.documents.map(summarizeDocument),
      this.store.findVolumes(scope, created.project.id),
    );
  }

  /** Projects of the principal, most recently updated first. */
  listProjects(principal: Principal): Record<string, unknown>[] {
    return this.store
      .findProjects(scopeForPrincipal(principal))
      .map((project) => projectPayload(project));
  }

  /** Partially replace Project settings scalars without materializing its shell. */
  updateProject(
    principal: Principal,
    projectId: string,
    input: {
      title?: string | undefined;
      description?: string | undefined;
      settings?: Record<string, unknown> | undefined;
    },
  ): Record<string, unknown> {
    const title = input.title?.trim();
    if (title === "") {
      throw new InvalidProjectUpdateError("Project title is required.");
    }
    const description = input.description?.trim();
    const updated = this.store.updateProject(scopeForPrincipal(principal), projectId, {
      ...(title === undefined ? {} : { title }),
      ...(description === undefined ? {} : { description }),
      ...(input.settings === undefined ? {} : { settingsJson: dumpJson(input.settings) }),
      now: this.now(),
    });
    return projectPayload(updated);
  }

  /** Bounded structural shell in canonical document and volume order. */
  projectShell(
    principal: Principal,
    projectId: string,
  ): { payload: Record<string, unknown>; documents: DocumentSummaryRecord[] } {
    const scope = scopeForPrincipal(principal);
    const shell = this.store.readProjectShell(scope, projectId);
    return {
      payload: projectShellPayload(shell.project, shell.documents, shell.volumes),
      documents: shell.documents,
    };
  }

  /** Delete database authority, then converge its secondary export tree. */
  async removeProject(
    principal: Principal,
    projectId: string,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<void> {
    const scope = scopeForPrincipal(principal);
    // Authorize before consulting the process-local guard so another owner's
    // in-flight operation is never disclosed through a 409 response.
    this.store.findProject(scope, projectId);
    const permit = this.inFlight.acquireProjectExclusive(projectId, "project deletion");
    try {
      this.store.dropProject(scope, projectId);
      if (this.artifactCleaner === undefined) return;
      try {
        await this.artifactCleaner.removeProjectArtifacts(projectId);
      } catch (failure) {
        try {
          reportCleanupFailure?.(failure);
        } catch {
          // SQLite already committed. Startup reconciliation owns eventual
          // cleanup, so reporting failure cannot change the DELETE outcome.
        }
      }
    } finally {
      permit.release();
    }
  }
}
