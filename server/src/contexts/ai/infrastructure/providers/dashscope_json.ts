import { TextGenerationProviderError } from "../../application/ports/text_generation.js";

const MIN_FENCED_BLOCK_LINES = 3;

type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseJsonValue(candidate: string): unknown | undefined {
  try {
    return JSON.parse(candidate) as unknown;
  } catch {
    return undefined;
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
export function parseDashscopeJsonObject(rawText: string): JsonObject {
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
