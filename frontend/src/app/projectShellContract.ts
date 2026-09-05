import { LORE_STATUSES } from "@/app/loreStatus";
import type {
  DocumentKind,
  DocumentSummary,
  LoreStatus,
  ProjectListItem,
  ProjectShell,
  StudioDocument,
  Volume,
} from "@/app/types/studio";

import {
  arrayField,
  exactKeys,
  integerField,
  literalField,
  nonnegativeIntegerField,
  nullableStringField,
  objectValue,
  recordField,
  stringField,
} from "./apiContract";

const documentKinds = ["chapter", "outline", "character", "world", "note"] as const;
const revisionSources = ["author", "ai-accepted", "restore"] as const;

function parseDocument(value: unknown, label = "document"): StudioDocument {
  const item = objectValue(value, label);
  exactKeys(
    item,
    [
      "id",
      "project_id",
      "kind",
      "title",
      "position",
      "volume_id",
      "beat_ref",
      "lore_status",
      "current_revision_id",
      "content_markdown",
      "metadata",
      "revision_source",
      "word_count",
      "created_at",
      "updated_at",
    ],
    label,
  );
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    kind: literalField(item, "kind", label, documentKinds) as DocumentKind,
    title: stringField(item, "title", label),
    position: integerField(item, "position", label),
    volume_id: nullableStringField(item, "volume_id", label),
    beat_ref: nullableStringField(item, "beat_ref", label),
    current_revision_id: stringField(item, "current_revision_id", label),
    content_markdown: stringField(item, "content_markdown", label),
    metadata: recordField(item, "metadata", label),
    revision_source: literalField(item, "revision_source", label, revisionSources),
    word_count: nonnegativeIntegerField(item, "word_count", label),
    created_at: stringField(item, "created_at", label),
    updated_at: stringField(item, "updated_at", label),
    ...(item.lore_status === null
      ? { lore_status: null }
      : { lore_status: literalField(item, "lore_status", label, LORE_STATUSES) as LoreStatus }),
  };
}

const documentSummaryKeys = [
  "id",
  "project_id",
  "kind",
  "title",
  "position",
  "volume_id",
  "beat_ref",
  "lore_status",
  "current_revision_id",
  "revision_source",
  "word_count",
  "created_at",
  "updated_at",
] as const;

export function parseDocumentSummary(value: unknown, label = "document summary"): DocumentSummary {
  const item = objectValue(value, label);
  exactKeys(item, documentSummaryKeys, label);
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    kind: literalField(item, "kind", label, documentKinds) as DocumentKind,
    title: stringField(item, "title", label),
    position: integerField(item, "position", label),
    volume_id: nullableStringField(item, "volume_id", label),
    beat_ref: nullableStringField(item, "beat_ref", label),
    lore_status:
      item.lore_status === null
        ? null
        : (literalField(item, "lore_status", label, LORE_STATUSES) as LoreStatus),
    current_revision_id: stringField(item, "current_revision_id", label),
    revision_source: literalField(item, "revision_source", label, revisionSources),
    word_count: nonnegativeIntegerField(item, "word_count", label),
    created_at: stringField(item, "created_at", label),
    updated_at: stringField(item, "updated_at", label),
  };
}

export function parseVolume(value: unknown, label = "volume"): Volume {
  const item = objectValue(value, label);
  exactKeys(item, ["id", "project_id", "title", "position", "created_at", "updated_at"], label);
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    title: stringField(item, "title", label),
    position: integerField(item, "position", label),
    created_at: stringField(item, "created_at", label),
    updated_at: stringField(item, "updated_at", label),
  };
}

export function parseVolumes(value: unknown): { volumes: Volume[] } {
  const item = objectValue(value, "volumes response");
  return {
    volumes: arrayField(item, "volumes", "volumes response", (entry, index) =>
      parseVolume(entry, `volumes[${index}]`),
    ),
  };
}

const projectScalarKeys = [
  "id",
  "title",
  "description",
  "settings",
  "import_hash",
  "created_at",
  "updated_at",
] as const;

function projectScalars(item: Record<string, unknown>, label: string): ProjectListItem {
  return {
    id: stringField(item, "id", label),
    title: stringField(item, "title", label),
    description: stringField(item, "description", label),
    settings: recordField(item, "settings", label),
    import_hash: nullableStringField(item, "import_hash", label),
    created_at: stringField(item, "created_at", label),
    updated_at: stringField(item, "updated_at", label),
  };
}

export function parseProjectListItem(value: unknown, label = "project list item"): ProjectListItem {
  const item = objectValue(value, label);
  exactKeys(item, projectScalarKeys, label);
  return projectScalars(item, label);
}

export function parseProjectShell(value: unknown, label = "project shell"): ProjectShell {
  const item = objectValue(value, label);
  exactKeys(item, [...projectScalarKeys, "documents", "volumes"], label);
  return {
    ...projectScalars(item, label),
    documents: arrayField(item, "documents", label, (entry, index) =>
      parseDocumentSummary(entry, `${label}.documents[${index}]`),
    ),
    volumes: arrayField(item, "volumes", label, (entry, index) =>
      parseVolume(entry, `${label}.volumes[${index}]`),
    ),
  };
}

export const parseStudioDocument = parseDocument;

export function parseProjects(value: unknown): { projects: ProjectListItem[] } {
  const item = objectValue(value, "projects response");
  return {
    projects: arrayField(item, "projects", "projects response", (entry, index) =>
      parseProjectListItem(entry, `projects[${index}]`),
    ),
  };
}

export function parseDocumentSummaries(value: unknown): { documents: DocumentSummary[] } {
  const item = objectValue(value, "documents response");
  return {
    documents: arrayField(item, "documents", "documents response", (entry, index) =>
      parseDocumentSummary(entry, `documents[${index}]`),
    ),
  };
}

export const parseDocuments = parseDocumentSummaries;
