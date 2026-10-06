import { LORE_STATUSES } from "@/app/loreStatus";
import type { LoreExtractCandidate } from "@/app/types/lore";
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
  parseDocuments,
  parseProjectListItem,
  parseProjectShell,
  parseProjects,
  parseStudioDocument,
  parseVolume,
  parseVolumes,
} from "./projectShellContract";

/**
 * Raised when a successful response does not satisfy the frontend's runtime
 * contract. The `Invalid <label>` message stays byte-stable (the contract
 * tests locate it verbatim) while `label` lets the localized error surface
 * (DR-021) map the shape to a user-readable message per language and keep the
 * raw label as technical detail.
 */
export class ApiContractError extends Error {
  readonly label: string;

  constructor(label: string) {
    super(`Invalid ${label}`);
    Object.setPrototypeOf(this, ApiContractError.prototype);
    this.label = label;
  }
}

type JsonRecord = Record<string, unknown>;

const sessionKinds = ["owner"] as const;
const revisionSources = ["author", "ai-accepted", "restore"] as const;

function fail(label: string): never {
  throw new ApiContractError(label);
}

const isoUtcTimestamp = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z$/;

/** A string field that must be an exact UTC ISO timestamp. */
export function isoUtcStringField(source: JsonRecord, key: string, parent: string): string {
  const value = stringField(source, key, parent);
  const match = isoUtcTimestamp.exec(value);
  const parsed = new Date(value);
  if (
    match === null ||
    Number.isNaN(parsed.getTime()) ||
    parsed.getUTCFullYear() !== Number(match[1]) ||
    parsed.getUTCMonth() + 1 !== Number(match[2]) ||
    parsed.getUTCDate() !== Number(match[3]) ||
    parsed.getUTCHours() !== Number(match[4]) ||
    parsed.getUTCMinutes() !== Number(match[5]) ||
    parsed.getUTCSeconds() !== Number(match[6])
  ) {
    fail(`${parent}.${key}`);
  }
  return value;
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

export function field(source: JsonRecord, key: string, parent: string): unknown {
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

/** A number field that legitimately carries null (e.g. `next_offset`). */
export function nullableNumberField(
  source: JsonRecord,
  key: string,
  parent: string,
): number | null {
  const value = field(source, key, parent);
  if (value === null) return null;
  return typeof value === "number" && Number.isFinite(value) ? value : fail(`${parent}.${key}`);
}

function booleanField(source: JsonRecord, key: string, parent: string): boolean {
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

/** The lore-alias envelope (#315): one document's extra prompt keys. */
export function parseAliases(value: unknown): { aliases: string[] } {
  const item = objectValue(value, "aliases response");
  return {
    aliases: arrayField(item, "aliases", "aliases response", (entry, index) =>
      stringValue(entry, `aliases[${index}]`),
    ),
  };
}

const loreCandidateKinds = ["character", "world"] as const;

/**
 * The lore-extract job's candidate set (#614): present only on terminal
 * `lore-extract` jobs, always a `{kind, title, aliases, summary}` array —
 * suggestions, never persisted content. Absent on every other job result.
 */
export function parseLoreCandidates(
  source: Record<string, unknown>,
  label: string,
): LoreExtractCandidate[] | undefined {
  const value = source.candidates;
  if (value === undefined) return undefined;
  const rowLabel = (index: number) => `${label}.candidates[${index}]`;
  return arrayField(source, "candidates", label, (entry, index) => {
    const item = objectValue(entry, rowLabel(index));
    return {
      kind: literalField(item, "kind", rowLabel(index), loreCandidateKinds),
      title: stringField(item, "title", rowLabel(index)),
      aliases: arrayField(item, "aliases", rowLabel(index), (alias, aliasIndex) =>
        stringValue(alias, `${rowLabel(index)}.aliases[${aliasIndex}]`),
      ),
      summary: stringField(item, "summary", rowLabel(index)),
    };
  });
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

export function parseVoid(): void {}
