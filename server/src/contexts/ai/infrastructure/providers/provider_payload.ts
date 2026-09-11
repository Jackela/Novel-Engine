import { TextGenerationProviderError } from "../../application/ports/text_generation.js";

/**
 * Provider-neutral payload pipeline shared by every real HTTP adapter:
 * response text -> schema-conformant JSON payload. Migrated verbatim from
 * the dashscope_payload/dashscope_json namespaces; DashScope-specific
 * protocol handling stays in dashscope_protocol.ts.
 */
type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const MIN_FENCED_BLOCK_LINES = 3;

function parseJsonValue(candidate: string): unknown | undefined {
  try {
    return JSON.parse(candidate) as unknown;
  } catch (error) {
    if (error instanceof SyntaxError) return undefined;
    throw error;
  }
}

function extractBalancedFragments(text: string, opening: string, closing: string): string[] {
  const fragments: string[] = [];
  let depth = 0;
  let start = -1;
  let inString = false;
  let delimiter = "";
  let escaped = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index] ?? "";
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === delimiter) {
        inString = false;
      }
      continue;
    }
    if (character === '"' || character === "'") {
      inString = true;
      delimiter = character;
      continue;
    }
    if (character === opening) {
      if (depth === 0) start = index;
      depth += 1;
      continue;
    }
    if (character === closing && depth > 0) {
      depth -= 1;
      if (depth === 0 && start !== -1) {
        fragments.push(text.slice(start, index + 1).trim());
        start = -1;
      }
    }
  }
  return fragments;
}

function coerceParsedObjectCandidate(parsed: unknown): JsonObject | undefined {
  if (isJsonObject(parsed)) return parsed;
  if (typeof parsed === "string") {
    const nested = parseJsonValue(parsed.trim());
    return nested === undefined || nested === parsed
      ? undefined
      : coerceParsedObjectCandidate(nested);
  }
  if (!Array.isArray(parsed)) return undefined;

  const objects = parsed
    .map((item) => coerceParsedObjectCandidate(item))
    .filter((item): item is JsonObject => item !== undefined);
  return objects.length === 0 ? undefined : Object.assign({}, ...objects);
}

/**
 * Parse the object-shaped portion of a provider response without trusting prose
 * around it. The scanner balances brackets while respecting quoted strings so a
 * brace in generated text never truncates a valid JSON fragment.
 */
export function parseProviderJsonObject(rawText: string): JsonObject {
  const stripped = rawText.trim();
  const candidates = stripped === "" ? [] : [stripped];
  if (stripped.startsWith("```") && stripped.endsWith("```")) {
    const lines = stripped.split(/\r?\n/u);
    if (lines.length >= MIN_FENCED_BLOCK_LINES)
      candidates.push(lines.slice(1, -1).join("\n").trim());
  }
  candidates.push(...extractBalancedFragments(stripped, "{", "}"));
  candidates.push(...extractBalancedFragments(stripped, "[", "]"));

  const seen = new Set<string>();
  for (const candidate of candidates) {
    if (candidate === "" || seen.has(candidate)) continue;
    seen.add(candidate);
    const parsed = parseJsonValue(candidate);
    if (parsed === undefined) continue;
    const normalized = coerceParsedObjectCandidate(parsed);
    if (normalized !== undefined) return normalized;
  }
  throw new TextGenerationProviderError("DashScope response is not a JSON object");
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
    return parseProviderJsonObject(contentText);
  } catch (error) {
    if (!(error instanceof TextGenerationProviderError)) throw error;
    const fallback = fallbackPayloadFromNonObjectResponse(contentText, responseSchema);
    if (fallback !== undefined) return fallback;
    throw error;
  }
}
