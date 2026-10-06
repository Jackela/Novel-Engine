import { ApiContractError } from "./apiContract";
import { HttpError } from "./httpClient";
import type { MessageKey } from "./i18n/dictionaries/en";
import { getActiveLanguage, type Language } from "./i18n/language";
import { translate } from "./i18n/translate";
import { isRecord } from "./typeGuards";

/**
 * DR-021 localized error surface: the unified envelope's stable `error.code`
 * is the contract the UI may rely on, so it maps by name to a dictionary
 * message per language. The raw server/provider prose is withheld from the
 * primary message and stays reachable as `technical` detail for the
 * diagnostics channel and the UI's technical-details affordances.
 *
 * The catalog codes mirror `server/src/shared/domain/error_codes.ts`
 * (rendered in `docs/agents/error-codes.md`); the two extra entries are the
 * proposal stream's terminal frame code (`PROVIDER_FAILED`, declared in
 * `server/src/contexts/studio/application/payload_schemas/proposal_frame.ts`)
 * and the Fastify transport code for an oversized body. Names are pinned by
 * `localizeError.test.ts`, which reads the server catalog and fails on drift.
 */
export const ERROR_CODE_MESSAGE_KEYS = {
  UNAUTHORIZED: "errors.codeUnauthorized",
  FORBIDDEN: "errors.codeForbidden",
  SETUP_TOKEN_INVALID: "errors.codeSetupTokenInvalid",
  CSRF_TOKEN_MISSING: "errors.codeCsrfTokenMissing",
  CSRF_TOKEN_INVALID: "errors.codeCsrfTokenInvalid",
  RATE_LIMIT_EXCEEDED: "errors.codeRateLimited",
  NOT_FOUND: "errors.codeNotFound",
  INVALID_OPERATION: "errors.codeInvalidOperation",
  PROVIDER_NOT_CONFIGURED: "errors.codeProviderNotConfigured",
  EXPORT_CAPACITY_EXCEEDED: "errors.codeExportCapacity",
  GENERATION_CAPACITY_EXCEEDED: "errors.codeGenerationCapacity",
  IMPORT_CAPACITY_EXCEEDED: "errors.codeImportCapacity",
  STRUCTURE_CAPACITY_EXCEEDED: "errors.codeStructureCapacity",
  VALIDATION_ERROR: "errors.codeValidation",
  REVISION_CONFLICT: "errors.codeRevisionConflict",
  VOLUME_CONFLICT: "errors.codeVolumeConflict",
  SNAPSHOT_CONFLICT: "errors.codeSnapshotConflict",
  DOCUMENT_CONFLICT: "errors.codeDocumentConflict",
  OPERATION_IN_FLIGHT: "errors.codeOperationInFlight",
  OPERATION_CAPACITY_EXCEEDED: "errors.codeOperationCapacity",
  SERVICE_UNAVAILABLE: "errors.codeServiceUnavailable",
  INTERNAL_ERROR: "errors.codeInternal",
  PROVIDER_FAILED: "errors.codeProviderFailed",
  FST_ERR_CTP_BODY_TOO_LARGE: "errors.codePayloadTooLarge",
} as const satisfies Record<string, MessageKey>;

export type KnownErrorCode = keyof typeof ERROR_CODE_MESSAGE_KEYS;

/**
 * Capacity resource identifiers by the names the server catalogs emit
 * (`structure_capacity.ts`, `exceptions.ts`, `generation_capacity_policy.ts`,
 * `legacy_workspace_fs_guard.ts`). Unlisted identifiers degrade to the
 * code-level generic message instead of leaking the raw identifier.
 */
const CAPACITY_RESOURCE_KEYS: Readonly<Record<string, MessageKey>> = {
  project_documents: "errors.resourceProjectDocuments",
  project_volumes: "errors.resourceProjectVolumes",
  volume_chapters: "errors.resourceVolumeChapters",
  project_settings_bytes: "errors.resourceProjectSettingsBytes",
  document_metadata_bytes: "errors.resourceDocumentMetadataBytes",
  outline_beats: "errors.resourceOutlineBeats",
  source_documents: "errors.resourceSourceDocuments",
  source_bytes: "errors.resourceSourceBytes",
  artifact_bytes: "errors.resourceArtifactBytes",
  manifest_bytes: "errors.resourceManifestBytes",
  prompt_bytes: "errors.resourcePromptBytes",
  lore_extract_segment: "errors.resourceLoreExtractSegment",
  story_bytes: "errors.resourceStoryBytes",
  chapter_bytes: "errors.resourceChapterBytes",
  workspace_bytes: "errors.resourceWorkspaceBytes",
  chapter_count: "errors.resourceChapterCount",
  directory_entries: "errors.resourceDirectoryEntries",
};

const CAPACITY_MESSAGE_KEYS = {
  EXPORT_CAPACITY_EXCEEDED: "errors.codeExportCapacity",
  GENERATION_CAPACITY_EXCEEDED: "errors.codeGenerationCapacity",
  IMPORT_CAPACITY_EXCEEDED: "errors.codeImportCapacity",
  STRUCTURE_CAPACITY_EXCEEDED: "errors.codeStructureCapacity",
} as const;

const CAPACITY_FALLBACK_KEYS = {
  EXPORT_CAPACITY_EXCEEDED: "errors.codeExportCapacityGeneric",
  GENERATION_CAPACITY_EXCEEDED: "errors.codeGenerationCapacityGeneric",
  IMPORT_CAPACITY_EXCEEDED: "errors.codeImportCapacityGeneric",
  STRUCTURE_CAPACITY_EXCEEDED: "errors.codeStructureCapacityGeneric",
} as const;

type CapacityCode = keyof typeof CAPACITY_MESSAGE_KEYS;

/**
 * Contract-layer label roots (`Invalid <label>.<key>`) mapped to the resource
 * noun the localized sentence names; labels that do not match degrade to the
 * generic contract message with the raw label kept as technical detail.
 */
const CONTRACT_LABEL_KEYS: Readonly<Record<string, MessageKey>> = {
  alias: "errors.contractAlias",
  chapter: "errors.contractChapter",
  document: "errors.contractDocument",
  export: "errors.contractExport",
  job: "errors.contractJob",
  lore: "errors.contractLore",
  owner: "errors.contractOwner",
  project: "errors.contractProject",
  proposal: "errors.contractProposal",
  review: "errors.contractReview",
  revision: "errors.contractRevision",
  search: "errors.contractSearch",
  session: "errors.contractSession",
  setup: "errors.contractSetup",
  usage: "errors.contractUsage",
  volume: "errors.contractVolume",
  writing: "errors.contractWriting",
};

/** The localized message plus the raw diagnostic text it withholds. */
export interface LocalizedError {
  readonly message: string;
  /** Raw server/provider text; null when the primary message replaced nothing. */
  readonly technical: string | null;
}

function detailNumber(details: Record<string, unknown> | undefined, key: string): number | null {
  const value = details?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function retryAfterSeconds(details: Record<string, unknown> | undefined): number | null {
  const seconds = detailNumber(details, "retry_after_seconds");
  return seconds !== null && seconds >= 0 ? seconds : null;
}

/** The envelope's closed capacity evidence `{resource, limit}` when readable. */
function capacityEvidence(
  details: Record<string, unknown> | undefined,
): { resource: string; limit: number } | null {
  if (details === undefined) return null;
  const { resource, limit } = details;
  if (typeof resource !== "string" || resource === "") return null;
  if (typeof limit !== "number" || !Number.isSafeInteger(limit) || limit < 0) return null;
  return { resource, limit };
}

/** The HTTP status a provider failure report quotes, when it quotes one. */
function providerHttpStatus(raw: string): number | null {
  const digits = /HTTP\s+(\d{3})/.exec(raw)?.[1];
  if (digits === undefined) return null;
  const status = Number(digits);
  return Number.isSafeInteger(status) ? status : null;
}

function capacityMessage(
  code: CapacityCode,
  details: Record<string, unknown> | undefined,
  language: Language,
): string {
  const evidence = capacityEvidence(details);
  const resourceKey = evidence === null ? undefined : CAPACITY_RESOURCE_KEYS[evidence.resource];
  if (evidence === null || resourceKey === undefined) {
    return translate(language, CAPACITY_FALLBACK_KEYS[code]);
  }
  return translate(language, CAPACITY_MESSAGE_KEYS[code], {
    resource: translate(language, resourceKey),
    limit: evidence.limit,
  });
}

function mappedMessage(
  code: KnownErrorCode,
  details: Record<string, unknown> | undefined,
  raw: string,
  language: Language,
): string {
  // DR-022: the provider family's credential gap has its own message; every
  // other PROVIDER_* failure keeps the transport-status mapping below.
  if (code === "PROVIDER_NOT_CONFIGURED") {
    return translate(language, "errors.codeProviderNotConfigured");
  }
  if (code.startsWith("PROVIDER_")) {
    const status = providerHttpStatus(raw);
    return status === null
      ? translate(language, "errors.codeProviderFailedGeneric")
      : translate(language, "errors.codeProviderFailed", { status });
  }
  switch (code) {
    case "RATE_LIMIT_EXCEEDED": {
      const seconds = retryAfterSeconds(details);
      return seconds === null
        ? translate(language, "errors.codeRateLimitedGeneric")
        : translate(language, "errors.codeRateLimited", { seconds });
    }
    case "OPERATION_CAPACITY_EXCEEDED": {
      const seconds = retryAfterSeconds(details);
      const limit = detailNumber(details, "limit");
      return seconds === null || limit === null
        ? translate(language, "errors.codeOperationCapacityGeneric")
        : translate(language, "errors.codeOperationCapacity", { limit, seconds });
    }
    case "EXPORT_CAPACITY_EXCEEDED":
    case "GENERATION_CAPACITY_EXCEEDED":
    case "IMPORT_CAPACITY_EXCEEDED":
    case "STRUCTURE_CAPACITY_EXCEEDED":
      return capacityMessage(code, details, language);
    case "VALIDATION_ERROR": {
      const errors = details?.errors;
      const count = Array.isArray(errors) ? errors.length : null;
      return count === null
        ? translate(language, "errors.codeValidationGeneric")
        : translate(language, "errors.codeValidation", { count });
    }
    case "INTERNAL_ERROR": {
      const errorId = details?.error_id;
      return typeof errorId === "string" && errorId !== ""
        ? translate(language, "errors.codeInternal", { error_id: errorId })
        : translate(language, "errors.codeInternalGeneric");
    }
    default:
      return translate(language, ERROR_CODE_MESSAGE_KEYS[code]);
  }
}

function contractLabelKey(label: string): MessageKey | null {
  const head = (label.split(".")[0] ?? "").split("[")[0]?.trim() ?? "";
  const root = (head.split(/[\s:]+/)[0] ?? "").toLowerCase();
  const candidates = [
    root,
    root.endsWith("es") ? root.slice(0, -2) : root,
    root.endsWith("s") ? root.slice(0, -1) : root,
  ];
  for (const candidate of candidates) {
    const key = CONTRACT_LABEL_KEYS[candidate];
    if (key !== undefined) return key;
  }
  return null;
}

function contractMessage(label: string, language: Language): string {
  const resourceKey = contractLabelKey(label);
  return resourceKey === null
    ? translate(language, "errors.contractDataGeneric")
    : translate(language, "errors.contractData", { resource: translate(language, resourceKey) });
}

function isKnownErrorCode(code: string): code is KnownErrorCode {
  return Object.hasOwn(ERROR_CODE_MESSAGE_KEYS, code);
}

/**
 * Reduce any caught reason to the localized message the UI shows and the raw
 * diagnostic text it withholds. Non-errors degrade to the caller's fallback;
 * ordinary errors keep their own message; a coded envelope resolves through
 * the mapping table, an unknown code degrades to a readable generic message
 * that still names the code, and a 413 body refusal stays readable even
 * without a catalog code. `technical` is null only when nothing was withheld,
 * so callers can forward it to the diagnostics channel without noise.
 */
export function localizeError(
  reason: unknown,
  fallback: string,
  language?: Language,
): LocalizedError {
  if (!(reason instanceof Error)) return { message: fallback, technical: null };
  const activeLanguage = language ?? getActiveLanguage();
  if (reason instanceof ApiContractError) {
    return { message: contractMessage(reason.label, activeLanguage), technical: reason.message };
  }
  if (!(reason instanceof HttpError)) return { message: reason.message, technical: null };
  if (reason.status === 413) {
    return {
      message: translate(activeLanguage, "errors.codePayloadTooLarge"),
      technical: reason.message,
    };
  }
  const code = reason.code;
  if (code === undefined || code === "") return { message: reason.message, technical: null };
  const details = isRecord(reason.detail) ? reason.detail : undefined;
  if (isKnownErrorCode(code)) {
    return {
      message: mappedMessage(code, details, reason.message, activeLanguage),
      technical: code.startsWith("PROVIDER_") ? reason.message : null,
    };
  }
  return {
    message: translate(activeLanguage, "errors.codeUnknown", { code }),
    technical: reason.message,
  };
}
