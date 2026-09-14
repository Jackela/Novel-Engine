import { arrayField, isoUtcStringField, objectValue, stringField } from "@/app/apiContract";
import type { DiagnosticsSummary } from "@/app/types/studio";

function booleanMember(source: Record<string, unknown>, key: string, parent: string): boolean {
  const value = source[key];
  if (typeof value !== "boolean") throw new Error(`Invalid ${parent}.${key}`);
  return value;
}

/**
 * Runtime-validate the diagnostics export (#654) at the API boundary: every
 * member is a string, boolean, or nested record of those — the same
 * structural redaction the server schema guarantees.
 */
export function parseDiagnostics(value: unknown): DiagnosticsSummary {
  const item = objectValue(value, "diagnostics response");
  const label = "diagnostics response";
  return {
    generated_at: isoUtcStringField(item, "generated_at", label),
    product: parseDiagnosticsProduct(item.product, `${label}.product`),
    runtime: parseDiagnosticsRuntime(item.runtime, `${label}.runtime`),
    configuration: parseDiagnosticsConfiguration(item.configuration, `${label}.configuration`),
    database: parseDiagnosticsDatabase(item.database, `${label}.database`),
    recent_errors: arrayField(item, "recent_errors", label, (entry, index) => {
      const error = objectValue(entry, `${label}.recent_errors[${index}]`);
      return {
        message: stringField(error, "message", `${label}.recent_errors[${index}]`),
        occurred_at: isoUtcStringField(error, "occurred_at", `${label}.recent_errors[${index}]`),
      };
    }),
  };
}

function parseDiagnosticsProduct(value: unknown, label: string): DiagnosticsSummary["product"] {
  const item = objectValue(value, label);
  return {
    name: stringField(item, "name", label),
    version: stringField(item, "version", label),
  };
}

function parseDiagnosticsRuntime(value: unknown, label: string): DiagnosticsSummary["runtime"] {
  const item = objectValue(value, label);
  return {
    platform: stringField(item, "platform", label),
    architecture: stringField(item, "architecture", label),
    node_version: stringField(item, "node_version", label),
  };
}

function parseDiagnosticsConfiguration(
  value: unknown,
  label: string,
): DiagnosticsSummary["configuration"] {
  const item = objectValue(value, label);
  const provider = objectValue(item.provider, `${label}.provider`);
  const keys = objectValue(item.keys, `${label}.keys`);
  return {
    provider: {
      id: stringField(provider, "id", `${label}.provider`),
      label: stringField(provider, "label", `${label}.provider`),
      configured: booleanMember(provider, "configured", `${label}.provider`),
    },
    keys: {
      session_secret: booleanMember(keys, "session_secret", `${label}.keys`),
      dashscope_api_key: booleanMember(keys, "dashscope_api_key", `${label}.keys`),
      openai_compatible_api_key: booleanMember(keys, "openai_compatible_api_key", `${label}.keys`),
    },
  };
}

function parseDiagnosticsDatabase(value: unknown, label: string): DiagnosticsSummary["database"] {
  const item = objectValue(value, label);
  return {
    quick_check: stringField(item, "quick_check", label),
    journal_mode: stringField(item, "journal_mode", label),
    foreign_keys: booleanMember(item, "foreign_keys", label),
    owner_configured: booleanMember(item, "owner_configured", label),
  };
}
