import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { dumpJson, projectPayload } from "./payloads.js";
import {
  type DocumentWithCurrent,
  type StudioStore,
  scopeForPrincipal,
} from "./ports/studio_store.js";

/** The adjudicated new-project seed (mirrors the Python authority). */
const SEED_DOCUMENT_TITLE = "Chapter 1";
const SEED_DOCUMENT_CONTENT = "# Chapter 1\n\n";
const DEFAULT_SETTINGS = dumpJson({ provider: "mock" });

export class ProjectService {
  private readonly store: StudioStore;
  private readonly now: () => Date;

  constructor(store: StudioStore, now: () => Date = () => new Date()) {
    this.store = store;
    this.now = now;
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
    return projectPayload(
      created.project,
      created.documents,
      this.store.findVolumes(scope, created.project.id),
    );
  }

  /** Projects of the principal, most recently updated first. */
  listProjects(principal: Principal): Record<string, unknown>[] {
    return this.store
      .findProjects(scopeForPrincipal(principal))
      .map((project) => projectPayload(project));
  }

  /** Project detail including its reading-order documents and volumes. */
  projectDetail(
    principal: Principal,
    projectId: string,
  ): { payload: Record<string, unknown>; documents: DocumentWithCurrent[] } {
    const scope = scopeForPrincipal(principal);
    const project = this.store.findProject(scope, projectId);
    const documents = this.store.findDocuments(scope, projectId);
    const payload = projectPayload(project, documents, this.store.findVolumes(scope, projectId));
    return { payload, documents };
  }

  /** Delete the project; dependent rows cascade and the export dir is removed. */
  removeProject(principal: Principal, projectId: string): void {
    this.store.dropProject(scopeForPrincipal(principal), projectId);
  }
}
