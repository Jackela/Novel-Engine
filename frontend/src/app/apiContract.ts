import { LORE_STATUSES } from "@/app/loreStatus";
import type {
  LoreStatus,
  ProviderInfo,
  RevisionPage,
  RevisionSummary,
  Session,
  SessionKind,
  SetupStatus,
} from "@/app/types/studio";

export {
  parseDocumentSummaries,
  parseDocumentSummary,
  parseDocuments,
  parseProjectListItem,
  parseProjectShell,
  parseProjects,
  parseStudioDocument,
  parseVolume,
  parseVolumes,
} from "./projectShellContract";

class ApiContractError extends Error {
  constructor(label: string) {
    super(`Invalid ${label}`);
    Object.setPrototypeOf(this, ApiContractError.prototype);
  }
}

type JsonRecord = Record<string, unknown>;

const sessionKinds = ["owner"] as const;
const revisionSources = ["author", "ai-accepted", "restore"] as const;

function fail(label: string): never {
  throw new ApiContractError(label);
}

export function exactKeys(source: JsonRecord, keys: readonly string[], label: string): void {
  for (const key of keys) {
    if (!Object.hasOwn(source, key)) fail(`${label}.${key}`);
  }
  const actual = Object.keys(source);
  const allowedKeys = new Set(keys);
  if (actual.length !== keys.length || actual.some((key) => !allowedKeys.has(key))) {
    fail(`${label} keys`);
  }
}

export function integerField(source: JsonRecord, key: string, parent: string): number {
  const value = field(source, key, parent);
  return typeof value === "number" && Number.isInteger(value) ? value : fail(`${parent}.${key}`);
}

export function nonnegativeIntegerField(source: JsonRecord, key: string, parent: string): number {
  const value = integerField(source, key, parent);
  return value >= 0 ? value : fail(`${parent}.${key}`);
}

export function objectValue(value: unknown, label: string): JsonRecord {
  if (typeof value !== "object" || value === null || Array.isArray(value)) fail(label);
  return value as JsonRecord;
}

function field(source: JsonRecord, key: string, parent: string): unknown {
  if (!Object.hasOwn(source, key)) fail(`${parent}.${key}`);
  return source[key];
}

export function stringValue(value: unknown, label: string): string {
  return typeof value === "string" ? value : fail(label);
}

export function stringField(source: JsonRecord, key: string, parent: string): string {
  return stringValue(field(source, key, parent), `${parent}.${key}`);
}

export function nullableString(value: unknown, label: string): string | null {
  return value === null ? null : stringValue(value, label);
}

export function nullableStringField(
  source: JsonRecord,
  key: string,
  parent: string,
): string | null {
  return nullableString(field(source, key, parent), `${parent}.${key}`);
}

export function numberField(source: JsonRecord, key: string, parent: string): number {
  const value = field(source, key, parent);
  return typeof value === "number" && Number.isFinite(value) ? value : fail(`${parent}.${key}`);
}

export function booleanField(source: JsonRecord, key: string, parent: string): boolean {
  const value = field(source, key, parent);
  return typeof value === "boolean" ? value : fail(`${parent}.${key}`);
}

export function recordField(
  source: JsonRecord,
  key: string,
  parent: string,
): Record<string, unknown> {
  return objectValue(field(source, key, parent), `${parent}.${key}`);
}

function arrayValue<T>(
  value: unknown,
  label: string,
  parseItem: (item: unknown, index: number) => T,
): T[] {
  return Array.isArray(value) ? value.map(parseItem) : fail(label);
}

export function arrayField<T>(
  source: JsonRecord,
  key: string,
  parent: string,
  parseItem: (item: unknown, index: number) => T,
): T[] {
  return arrayValue(field(source, key, parent), `${parent}.${key}`, parseItem);
}

function literalValue<T extends readonly string[]>(
  value: unknown,
  allowed: T,
  label: string,
): T[number] {
  return typeof value === "string" && allowed.includes(value) ? (value as T[number]) : fail(label);
}

export function literalField<T extends readonly string[]>(
  source: JsonRecord,
  key: string,
  parent: string,
  allowed: T,
): T[number] {
  return literalValue(field(source, key, parent), allowed, `${parent}.${key}`);
}

/** The lore lifecycle-status envelope (#444): one document's closed status. */
export function parseLoreStatus(value: unknown): { lore_status: LoreStatus } {
  const item = objectValue(value, "lore status response");
  return {
    lore_status: literalField(
      item,
      "lore_status",
      "lore status response",
      LORE_STATUSES,
    ) as LoreStatus,
  };
}

/** One resolved outline beat in the chapter-beat view (#313). */
export interface LinkedBeat {
  title: string;
  content: string;
}

/**
 * The chapter-beat envelope (#313): the resolved association view — the live
 * outline beat, or null when unlinked or vanished. The view is display-only;
 * `beat_ref` authority is the command's normalized requested value (#466).
 */
export function parseChapterBeat(value: unknown): { beat: LinkedBeat | null } {
  const item = objectValue(value, "chapter beat response");
  const beat = field(item, "beat", "chapter beat response");
  if (beat === null) return { beat: null };
  const linked = objectValue(beat, "chapter beat response.beat");
  return {
    beat: {
      title: stringField(linked, "title", "chapter beat response.beat"),
      content: stringField(linked, "content", "chapter beat response.beat"),
    },
  };
}

/** The lore-alias envelope (#315): one document's extra prompt keys. */
export function parseAliases(value: unknown): { aliases: string[] } {
  const item = objectValue(value, "aliases response");
  return {
    aliases: arrayField(item, "aliases", "aliases response", (entry, index) =>
      stringValue(entry, `aliases[${index}]`),
    ),
  };
}

export function parseSetupStatus(value: unknown): SetupStatus {
  const item = objectValue(value, "setup");
  return {
    owner_configured: booleanField(item, "owner_configured", "setup"),
    name: stringField(item, "name", "setup"),
    version: stringField(item, "version", "setup"),
  };
}

export function parseOwnerSetup(value: unknown): {
  id: string;
  username: string;
} {
  const item = objectValue(value, "owner");
  return {
    id: stringField(item, "id", "owner"),
    username: stringField(item, "username", "owner"),
  };
}

export function parseSession(value: unknown): Session {
  const item = objectValue(value, "session");
  return {
    session_id: stringField(item, "session_id", "session"),
    kind: literalField(item, "kind", "session", sessionKinds) as SessionKind,
    owner_id: nullableStringField(item, "owner_id", "session"),
    expires_at: nullableStringField(item, "expires_at", "session"),
  };
}

function parseProvider(value: unknown, label: string): ProviderInfo {
  const item = objectValue(value, label);
  return {
    provider: stringField(item, "provider", label),
    configured: booleanField(item, "configured", label),
    model: nullableStringField(item, "model", label),
    is_default: booleanField(item, "is_default", label),
  };
}

export function parseProviders(value: unknown): { providers: ProviderInfo[] } {
  const item = objectValue(value, "providers response");
  return {
    providers: arrayField(item, "providers", "providers response", (entry, index) =>
      parseProvider(entry, `providers[${index}]`),
    ),
  };
}

function parseRevisionSummary(value: unknown, label: string): RevisionSummary {
  const item = objectValue(value, label);
  return {
    id: stringField(item, "id", label),
    document_id: stringField(item, "document_id", label),
    parent_revision_id: nullableStringField(item, "parent_revision_id", label),
    revision_number: numberField(item, "revision_number", label),
    source: literalField(item, "source", label, revisionSources),
    word_count: numberField(item, "word_count", label),
    created_at: stringField(item, "created_at", label),
  };
}

export function parseRevisions(value: unknown): RevisionPage {
  const item = objectValue(value, "revisions response");
  return {
    revisions: arrayField(item, "revisions", "revisions response", (entry, index) =>
      parseRevisionSummary(entry, `revisions[${index}]`),
    ),
    next_cursor: nullableStringField(item, "next_cursor", "revisions response"),
  };
}

export function parseSearch(value: unknown): {
  results: Array<{ document_id: string; title: string; excerpt: string }>;
} {
  const item = objectValue(value, "search response");
  return {
    results: arrayField(item, "results", "search response", (entry, index) => {
      const result = objectValue(entry, `results[${index}]`);
      return {
        document_id: stringField(result, "document_id", `results[${index}]`),
        title: stringField(result, "title", `results[${index}]`),
        excerpt: stringField(result, "excerpt", `results[${index}]`),
      };
    }),
  };
}

export function parseVoid(): void {}
