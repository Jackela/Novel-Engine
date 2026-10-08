import { TextGenerationProviderError } from "../../application/ports/text_generation.js";

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function conforms(value: unknown, schema: unknown): boolean {
  if (schema === "string" || schema === "number" || schema === "boolean")
    return typeof value === schema;
  if (Array.isArray(schema))
    return (
      Array.isArray(value) &&
      value.every((entry) => schema.length === 0 || conforms(entry, schema[0]))
    );
  if (!object(schema)) return true;
  if (schema.type === "string") return typeof value === "string";
  if (schema.type === "integer") return typeof value === "number" && Number.isSafeInteger(value);
  if (schema.type === "array")
    return Array.isArray(value) && value.every((entry) => conforms(entry, schema.items));
  const fields = schema.type === "object" && object(schema.properties) ? schema.properties : schema;
  return (
    object(value) &&
    Object.entries(fields).every(
      ([key, shape]) => key === "type" || (key in value && conforms(value[key], shape)),
    )
  );
}
/** ACP alone may prefix output with progress prose; only one complete schema-valid JSON object reaches the business port. */
export class AcpJsonResponse {
  private prefix = "";
  private started = false;
  private complete = false;
  private quoted = false;
  private escaped = false;
  private depth = 0;
  private json = "";
  private readonly start: RegExp;
  constructor(private readonly schema: Record<string, unknown>) {
    const key = Object.keys(schema)[0];
    if (key === undefined || !/^[a-z_]+$/u.test(key))
      throw new TextGenerationProviderError("ACP task requires a known structured response key.");
    this.start = new RegExp(`\\{\\s*"${key}"\\s*:`, "u");
  }
  feed(fragment: string): string | undefined {
    if (!this.started) {
      this.prefix += fragment;
      if (Buffer.byteLength(this.prefix, "utf8") > 64 * 1024)
        throw new TextGenerationProviderError("ACP progress prefix exceeds its byte budget.");
      const match = this.start.exec(this.prefix);
      if (match === null) return undefined;
      fragment = this.prefix.slice(match.index);
      this.prefix = "";
      this.started = true;
    }
    let emitted = "";
    for (const character of fragment) {
      if (this.complete) {
        if (!/\s/u.test(character))
          throw new TextGenerationProviderError(
            "ACP response contains an extra object or trailing non-JSON output.",
          );
        continue;
      }
      emitted += character;
      if (this.quoted) {
        if (this.escaped) this.escaped = false;
        else if (character === "\\") this.escaped = true;
        else if (character === '"') this.quoted = false;
      } else if (character === '"') this.quoted = true;
      else if (character === "{") this.depth += 1;
      else if (character === "}") {
        this.depth -= 1;
        if (this.depth === 0) this.complete = true;
      }
    }
    this.json += emitted;
    if (Buffer.byteLength(this.json, "utf8") > 16 * 1024 * 1024)
      throw new TextGenerationProviderError("ACP response exceeds its byte budget.");
    return emitted === "" ? undefined : emitted;
  }
  finish(): string {
    if (!this.complete)
      throw new TextGenerationProviderError(
        "ACP response ended without a complete structured JSON object.",
      );
    let parsed: unknown;
    try {
      parsed = JSON.parse(this.json);
    } catch (error) {
      if (!(error instanceof SyntaxError)) throw error;
      throw new TextGenerationProviderError("ACP response is not valid JSON.");
    }
    if (
      !object(parsed) ||
      Object.keys(parsed).length !== Object.keys(this.schema).length ||
      !conforms(parsed, this.schema)
    )
      throw new TextGenerationProviderError("ACP response does not conform to the task schema.");
    return this.json;
  }
}
