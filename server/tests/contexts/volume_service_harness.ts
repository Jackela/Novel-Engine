/**
 * Fixtures and dependency fakes for the direct VolumeService contract tests
 * (`volume_service.test.ts`). Kept outside the vitest test-file glob on
 * purpose, mirroring `writing_stats_harness.ts`; the file-size gate measures
 * each source file separately, so the assertions stay in the test file. The
 * fake store records every command through `Pick<StudioVolumeStore, ...>`, so
 * its methods are checked against the real port signatures.
 */
import type { DocumentWithCurrent } from "../../src/contexts/studio/application/ports/document_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import type {
  AddVolumeInput,
  AlterVolumeInput,
  PlaceDocumentInput,
  StudioVolumeStore,
  VolumeRecord,
} from "../../src/contexts/studio/application/ports/volume_store.js";
import { VolumeService } from "../../src/contexts/studio/application/volume_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

export const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};
export const SCOPE: ProjectScope = { ownerId: "owner-1" };
export const NOW = new Date("2026-09-03T00:00:00.000Z");
export const PROJECT_ID = "project-1";

export function volumeRecord(id: string, title: string, position: number): VolumeRecord {
  return { id, projectId: PROJECT_ID, title, position, createdAt: NOW, updatedAt: NOW };
}

export function volumeProjection(volume: VolumeRecord): Record<string, unknown> {
  return {
    id: volume.id,
    project_id: volume.projectId,
    title: volume.title,
    position: volume.position,
    created_at: NOW.toISOString(),
    updated_at: NOW.toISOString(),
  };
}

export function chapterDocument(overrides: Partial<DocumentWithCurrent> = {}): DocumentWithCurrent {
  return {
    id: "document-1",
    projectId: PROJECT_ID,
    kind: "chapter",
    title: "Chapter One",
    position: 3,
    volumeId: "volume-2",
    beatRef: null,
    loreAliasesJson: "[]",
    loreStatus: "draft",
    currentRevisionId: "revision-1",
    createdAt: NOW,
    updatedAt: NOW,
    currentRevision: {
      id: "revision-1",
      documentId: "document-1",
      parentRevisionId: null,
      revisionNumber: 1,
      contentMarkdown: "The harbour kept its own time.",
      metadataJson: '{"scene":"harbor"}',
      source: "author",
      wordCount: 6,
      createdAt: NOW,
    },
    ...overrides,
  };
}

export const CHAPTER_PAYLOAD = {
  id: "document-1",
  project_id: PROJECT_ID,
  kind: "chapter",
  title: "Chapter One",
  position: 3,
  volume_id: "volume-2",
  beat_ref: null,
  lore_status: null,
  current_revision_id: "revision-1",
  content_markdown: "The harbour kept its own time.",
  metadata: { scene: "harbor" },
  revision_source: "author",
  word_count: 6,
  created_at: NOW.toISOString(),
  updated_at: NOW.toISOString(),
};

type Fakes = Pick<
  StudioVolumeStore,
  | "findVolumes"
  | "addVolume"
  | "alterVolume"
  | "dropVolume"
  | "placeDocumentInVolume"
  | "renumberVolumes"
  | "renumberDocuments"
>;
export type ListCall = [ProjectScope, string];
export type AddCall = [ProjectScope, string, AddVolumeInput];
export type AlterCall = [ProjectScope, string, string, AlterVolumeInput];
export type DropCall = [ProjectScope, string, string];
export type PlaceCall = [ProjectScope, string, string, PlaceDocumentInput];
export type RenumberCall = [ProjectScope, string, string[], Date];

export interface HarnessConfig {
  volumes?: VolumeRecord[];
  added?: VolumeRecord | Error;
  altered?: VolumeRecord | Error;
  dropFailure?: Error;
  placed?: DocumentWithCurrent | Error;
  renumbered?: VolumeRecord[] | Error;
}

export function volumeHarness(config: HarnessConfig = {}) {
  const lists: ListCall[] = [];
  const adds: AddCall[] = [];
  const alters: AlterCall[] = [];
  const drops: DropCall[] = [];
  const places: PlaceCall[] = [];
  const renumbers: RenumberCall[] = [];
  let clockCalls = 0;
  const outcome = <T>(value: T | Error | undefined, fallback: T): T => {
    if (value instanceof Error) throw value;
    return value === undefined ? fallback : value;
  };
  const store: Fakes = {
    findVolumes: (scope, projectId) => {
      lists.push([scope, projectId]);
      return config.volumes ?? [];
    },
    addVolume: (scope, projectId, input) => {
      adds.push([scope, projectId, input]);
      return outcome(config.added, volumeRecord("volume-new", input.title, 1));
    },
    alterVolume: (scope, projectId, volumeId, input) => {
      alters.push([scope, projectId, volumeId, input]);
      return outcome(config.altered, volumeRecord(volumeId, input.title, 1));
    },
    dropVolume: (scope, projectId, volumeId) => {
      drops.push([scope, projectId, volumeId]);
      if (config.dropFailure !== undefined) throw config.dropFailure;
    },
    placeDocumentInVolume: (scope, projectId, documentId, input) => {
      places.push([scope, projectId, documentId, input]);
      return outcome(config.placed, chapterDocument({ volumeId: input.volumeId }));
    },
    renumberVolumes: (scope, projectId, volumeIds, now) => {
      renumbers.push([scope, projectId, volumeIds, now]);
      return outcome(
        config.renumbered,
        volumeIds.map((id, index) => volumeRecord(id, `Volume ${index + 1}`, index + 1)),
      );
    },
    renumberDocuments: () => {
      throw new Error("the volume surface must never renumber documents");
    },
  };
  const service = new VolumeService(store as unknown as StudioVolumeStore, () => {
    clockCalls += 1;
    return NOW;
  });
  return {
    service,
    lists,
    adds,
    alters,
    drops,
    places,
    renumbers,
    clockCalls: () => clockCalls,
  };
}
