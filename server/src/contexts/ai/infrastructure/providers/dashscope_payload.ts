import { TextGenerationProviderError } from "../../application/ports/text_generation.js";
import { parseDashscopeJsonObject } from "./dashscope_json.js";

type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function coerceObjectValue(value: unknown, schema: JsonObject, key: string | undefined): unknown {
  if (isJsonObject(value)) {
    const properties = schema.properties;
    if (!isJsonObject(properties)) return value;
    const normalized: JsonObject = { ...value };
    for (const [nestedKey, nestedSchema] of Object.entries(properties)) {
      if (nestedKey in normalized) {
        normalized[nestedKey] = coerceValueToSchema(normalized[nestedKey], nestedSchema, nestedKey);
      }
    }
    return normalized;
  }
  if (Array.isArray(value))
    return key === "character_bible" ? { characters: value } : { items: value };
  return value === null || value === "" ? {} : { value };
}

function coerceArrayValue(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  return value === null ? [] : [value];
}

function coerceStringValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value.trim();
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item).trim())
      .filter((item) => item !== "")
      .join(" ");
  }
  if (isJsonObject(value)) return JSON.stringify(value).trim();
  return String(value).trim();
}

function coerceIntegerValue(value: unknown): unknown {
  const numeric =
    typeof value === "number" ? value : typeof value === "string" ? Number(value) : Number.NaN;
  return Number.isInteger(numeric) ? numeric : value;
}

function coerceValueToSchema(value: unknown, schema: unknown, key: string | undefined): unknown {
  if (!isJsonObject(schema)) return value;
  if (schema.type === "object") return coerceObjectValue(value, schema, key);
  if (schema.type === "array") return coerceArrayValue(value);
  if (schema.type === "string") return coerceStringValue(value);
  if (schema.type === "integer") return coerceIntegerValue(value);
  return value;
}

/** Coerce only declared response fields into the shapes their schema accepts. */
export function coercePayloadToSchema(payload: JsonObject, responseSchema: JsonObject): JsonObject {
  const normalized: JsonObject = { ...payload };
  for (const [key, schema] of Object.entries(responseSchema)) {
    if (key in normalized) normalized[key] = coerceValueToSchema(normalized[key], schema, key);
  }
  return normalized;
}

function parseJsonValue(candidate: string): unknown | undefined {
  try {
    return JSON.parse(candidate) as unknown;
  } catch {
    return undefined;
  }
}

/**
 * Prose is only a valid recovery path for chapter markdown, whose contract
 * explicitly permits a plain narrative response from an HTTP provider.
 */
export function fallbackPayloadFromNonObjectResponse(
  rawText: string,
  responseSchema: JsonObject,
): JsonObject | undefined {
  const chapterSchema = responseSchema.chapter_markdown;
  if (!isJsonObject(chapterSchema) || chapterSchema.type !== "string") return undefined;

  const parsed = parseJsonValue(rawText.trim());
  const markdown =
    typeof parsed === "string"
      ? parsed.trim()
      : Array.isArray(parsed)
        ? parsed
            .filter((item): item is string => typeof item === "string" && item.trim() !== "")
            .map((item) => item.trim())
            .join("\n\n")
        : rawText.trim();
  return markdown === "" ? undefined : { chapter_markdown: markdown };
}

/** Parse structured provider text, retaining the explicit chapter-prose fallback. */
export function payloadFromResponseText(
  contentText: string,
  responseSchema: JsonObject,
): JsonObject {
  try {
    return parseDashscopeJsonObject(contentText);
  } catch (error) {
    if (!(error instanceof TextGenerationProviderError)) throw error;
    const fallback = fallbackPayloadFromNonObjectResponse(contentText, responseSchema);
    if (fallback !== undefined) return fallback;
    throw error;
  }
}
