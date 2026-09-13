import { TextGenerationProviderError } from "../../application/ports/text_generation.js";
import { isJsonObject, usageToken } from "./provider_http.js";

export type JsonObject = Record<string, unknown>;

function textFromContent(content: unknown): string | undefined {
  if (typeof content === "string") {
    const text = content.trim();
    return text === "" ? undefined : text;
  }
  if (!Array.isArray(content)) return undefined;
  const text = content
    .filter(
      (part): part is JsonObject =>
        isJsonObject(part) && typeof part.text === "string" && part.text.trim() !== "",
    )
    .map((part) => part.text as string)
    .join("")
    .trim();
  return text === "" ? undefined : text;
}

/** Extract the first structured message text from a native generation response. */
export function extractDashscopeGenerationText(data: JsonObject): string {
  const output = data.output;
  if (!isJsonObject(output))
    throw new TextGenerationProviderError("DashScope response missing output");

  const choices = output.choices;
  if (Array.isArray(choices) && choices.length > 0) {
    const firstChoice = choices[0];
    if (!isJsonObject(firstChoice)) {
      throw new TextGenerationProviderError("DashScope response choice is not an object");
    }
    const message = firstChoice.message;
    if (!isJsonObject(message)) {
      throw new TextGenerationProviderError("DashScope response message is not an object");
    }
    const text = textFromContent(message.content);
    if (text !== undefined) return text;
  }

  const outputText = output.text;
  if (typeof outputText === "string" && outputText.trim() !== "") return outputText.trim();
  throw new TextGenerationProviderError("DashScope response missing structured message content");
}

/** Extract a message item from the compatible Responses API shape. */
export function extractDashscopeResponsesText(data: JsonObject): string {
  const output = data.output;
  if (!Array.isArray(output)) {
    throw new TextGenerationProviderError("DashScope responses output is invalid");
  }
  for (const item of output) {
    if (!isJsonObject(item) || item.type !== "message") continue;
    const text = textFromContent(item.content);
    if (text !== undefined) return text;
  }
  throw new TextGenerationProviderError("DashScope responses output missing message text");
}

/**
 * Content text without trimming: stream deltas (#308) carry significant
 * whitespace, so unlike `textFromContent` nothing may be stripped.
 */
function rawTextFromContent(content: unknown): string | undefined {
  if (typeof content === "string") return content === "" ? undefined : content;
  if (!Array.isArray(content)) return undefined;
  const text = content
    .filter(
      (part): part is JsonObject =>
        isJsonObject(part) && typeof part.text === "string" && part.text !== "",
    )
    .map((part) => part.text as string)
    .join("");
  return text === "" ? undefined : text;
}

/**
 * One incremental text piece from an SSE stream chunk (#308), dispatched per
 * transport mode. Returns undefined for chunks without text (role prelude,
 * usage-only tail, keep-alives).
 */
export function extractDashscopeIncrementalText(data: JsonObject): string | undefined {
  return (
    extractResponsesStreamText(data) ??
    extractCompatibleModeStreamText(data) ??
    extractNativeGenerationStreamText(data)
  );
}

/** Responses events: a top-level string `delta`, then `output` list items. */
function extractResponsesStreamText(data: JsonObject): string | undefined {
  const topLevelDelta = data.delta;
  if (typeof topLevelDelta === "string" && topLevelDelta !== "") return topLevelDelta;
  const output = data.output;
  if (!Array.isArray(output)) return undefined;
  // Responses-mode events mirror the non-streaming shape (#343): output is a
  // list of items whose message content carries the incremental text.
  for (const item of output) {
    if (!isJsonObject(item)) continue;
    // #371: only message items expose content/text; typed non-message items
    // (reasoning, tool_call) are accepted solely via a top-level string
    // delta, mirroring OpenAI Responses event semantics. Untyped items keep
    // the pre-existing permissive extraction so older fixture shapes stay green.
    if (typeof item.type === "string" && item.type !== "message") {
      if (typeof item.delta === "string" && item.delta !== "") return item.delta;
      continue;
    }
    // Assumption: when a message item carries both `content` and `delta`,
    // `content` is authoritative and is returned first (#364 review minor #3).
    for (const holder of [item.message, item]) {
      if (!isJsonObject(holder)) continue;
      const text = rawTextFromContent(holder.content);
      if (text !== undefined) return text;
    }
    if (typeof item.delta === "string" && item.delta !== "") return item.delta;
    if (typeof item.text === "string" && item.text !== "") return item.text;
  }
  return undefined;
}

/** Compatible-mode chunks: the OpenAI delta shape under `choices[0]`. */
function extractCompatibleModeStreamText(data: JsonObject): string | undefined {
  const choices = Array.isArray(data.choices) ? data.choices : [];
  const firstChoice = choices.find(isJsonObject);
  if (firstChoice === undefined) return undefined;
  for (const holder of [firstChoice.delta, firstChoice.message]) {
    if (!isJsonObject(holder)) continue;
    const text = rawTextFromContent(holder.content);
    if (text !== undefined) return text;
  }
  return undefined;
}

/** Native `incremental_output` chunks: partial `output` message, or `output.text`. */
function extractNativeGenerationStreamText(data: JsonObject): string | undefined {
  const output = data.output;
  if (!isJsonObject(output)) return undefined;
  const outputChoices = Array.isArray(output.choices) ? output.choices : [];
  const outputChoice = outputChoices.find(isJsonObject);
  if (outputChoice !== undefined && isJsonObject(outputChoice.message)) {
    const text = rawTextFromContent(outputChoice.message.content);
    if (text !== undefined) return text;
  }
  if (typeof output.text === "string" && output.text !== "") return output.text;
  return undefined;
}

/** Read provider usage structurally; callers fall back to the shared word count when absent. */
export function extractDashscopeUsageTokens(
  data: JsonObject,
): readonly [number | null, number | null] {
  const usage = data.usage;
  if (!isJsonObject(usage)) return [null, null];
  return [
    usageToken(usage.prompt_tokens) ?? usageToken(usage.input_tokens),
    usageToken(usage.completion_tokens) ?? usageToken(usage.output_tokens),
  ];
}
