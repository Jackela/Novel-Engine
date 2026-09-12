import type { ExportArtifactGateway } from "../../contexts/studio/application/export_artifact_service.js";
import type { OperationCapacityPolicy } from "../../contexts/studio/application/operation_in_flight.js";
import type { ExportOutcomeStore } from "../../contexts/studio/application/ports/export_store.js";
import type { ProjectArtifactCleaner } from "../../contexts/studio/application/ports/project_artifact_cleaner.js";
import {
  createStudioServices,
  type StudioServices,
} from "../../contexts/studio/application/studio_services.js";
import { FilesystemExportArtifactGateway } from "../../contexts/studio/infrastructure/export_artifact_files.js";
import { DatabaseExportPublicationCleanupJournal } from "../../contexts/studio/infrastructure/export_publication_cleanup_journal.js";
import { ExportStorePart } from "../../contexts/studio/infrastructure/export_store_part.js";
import { FsLegacyWorkspaceReader } from "../../contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { FilesystemProjectArtifactCleaner } from "../../contexts/studio/infrastructure/project_artifact_files.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import type { StudioSqliteDatabase } from "../../shared/infrastructure/db/connection.js";
import { createStudioPersistence } from "../studio_persistence.js";
import type { PersistenceHandles } from "./persistence.js";
import type { ProviderRuntime } from "./provider_runtime.js";

export interface StudioServicesAssemblyOptions {
  /** Injectable time source for the session lifecycle (tests). */
  clock?: (() => Date) | undefined;
  /** Injectable export persistence factory for transaction/failure tests. */
  exportStoreFactory?: ((database: StudioSqliteDatabase) => ExportOutcomeStore) | undefined;
  /** Injectable artifact filesystem boundary for publication/failure tests. */
  exportArtifactGateway?: ExportArtifactGateway | undefined;
  /** Injectable post-commit project artifact cleanup boundary for tests. */
  projectArtifactCleaner?: ProjectArtifactCleaner | undefined;
  /**
   * Lorebook injection budget in characters (#445). Falls back to the
   * configured `LLM_LOREBOOK_BUDGET_CHARACTERS`, then the adjudicated default.
   */
  lorebookBudgetCharacters?: number | undefined;
}

/**
 * Private assembly of the Studio service container for the composition root:
 * one store part per narrow port plus the export/artifact boundaries, with
 * test seams overriding each filesystem or persistence edge.
 */
export function assembleStudioServices(
  persistence: PersistenceHandles,
  config: ServerConfig | undefined,
  provider: ProviderRuntime,
  operationCapacity: OperationCapacityPolicy | undefined,
  options: StudioServicesAssemblyOptions,
): StudioServices {
  const loreBudgetCharacters =
    options.lorebookBudgetCharacters ?? config?.llm.lorebookBudgetCharacters;
  return createStudioServices(createStudioPersistence(persistence.db.db), {
    now: options.clock,
    providerFactory: provider.providerFactory,
    legacyWorkspaceReader: new FsLegacyWorkspaceReader(),
    reviewProvenance: {
      provider: provider.defaultProvider,
      model: provider.reviewModel,
    },
    artifactStore:
      options.exportStoreFactory?.(persistence.db.db) ?? new ExportStorePart(persistence.db.db),
    artifactFiles:
      options.exportArtifactGateway ??
      new FilesystemExportArtifactGateway(persistence.dataDirectory, {
        cleanupJournal: new DatabaseExportPublicationCleanupJournal(persistence.db.db),
      }),
    projectArtifactCleaner:
      options.projectArtifactCleaner ??
      new FilesystemProjectArtifactCleaner(persistence.dataDirectory),
    loreBudgetCharacters,
    operationCapacity,
  });
}
