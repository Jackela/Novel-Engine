import type { TextGenerationTask } from "../../application/ports/text_generation.js";
import { buildSystemContent } from "./provider_json.js";

/** ACP tools preserve the task language for all prose-bearing result fields. */
export function buildAcpSystemContent(task: TextGenerationTask): string {
  const language = task.language === "zh" ? "Chinese" : "English";
  return `${buildSystemContent(task)}\nWrite prose, findings, suggestions and lore summaries in ${language}. Preserve JSON field names, enum values and document identifiers exactly as specified.`;
}
