import type { DashscopeTransportMode } from "./dashscope_transport.js";
import { isJsonObject } from "./provider_http.js";

const COMPATIBLE_FINISH_REASONS: ReadonlySet<string> = new Set([
  "stop",
  "length",
  "content_filter",
  "tool_calls",
  "function_call",
]);
const NATIVE_FINISH_REASONS: ReadonlySet<string> = new Set(["stop", "length", "tool_calls"]);

function firstChoiceFinishReason(choices: unknown): unknown {
  if (!Array.isArray(choices) || !isJsonObject(choices[0])) return undefined;
  return choices[0].finish_reason;
}

function recognizedReason(reason: unknown, allowed: ReadonlySet<string>): boolean {
  return typeof reason === "string" && allowed.has(reason);
}

/**
 * Recognize completion for the selected HTTP protocol. Null, malformed, or
 * misplaced reasons and local Responses item endings never establish success;
 * the caller must still consume later usage and provider error frames.
 */
export function isProviderStreamTerminal(
  chunk: Record<string, unknown>,
  mode: DashscopeTransportMode | "openai_compatible",
): boolean {
  if (mode === "responses") {
    return (
      chunk.type === "response.completed" &&
      isJsonObject(chunk.response) &&
      chunk.response.status === "completed"
    );
  }
  if (recognizedReason(firstChoiceFinishReason(chunk.choices), COMPATIBLE_FINISH_REASONS)) {
    return true;
  }
  if (mode === "openai_compatible" || !isJsonObject(chunk.output)) return false;
  const output = chunk.output;
  const reason = Array.isArray(output.choices)
    ? firstChoiceFinishReason(output.choices)
    : typeof output.text === "string"
      ? output.finish_reason
      : undefined;
  return recognizedReason(reason, NATIVE_FINISH_REASONS);
}
