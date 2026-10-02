import type {
  TextGenerationTask,
  WritingLanguage,
} from "../../application/ports/text_generation.js";

/**
 * The deterministic provider's language resolution (DR-023): a task that
 * carries no language is English, so every pre-existing task shape keeps
 * behaving exactly as before.
 */
export function taskWritingLanguage(task: TextGenerationTask): WritingLanguage {
  return task.language ?? "en";
}
