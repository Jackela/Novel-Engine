import { arrayField, numberField, objectValue, stringField } from "@/app/apiContract";
import type {
  WritingStats,
  WritingStatsDayRow,
  WritingStatsWeekRow,
  WritingStatsWords,
} from "@/app/types/studio";

/**
 * Runtime-validate the writing-statistics response (#653) at the API
 * boundary: word deltas stay signed integers because an author cut is an
 * honest negative figure, and every calendar key is a UTC day string.
 */
export function parseWritingStats(value: unknown): WritingStats {
  const item = objectValue(value, "writing stats response");
  const label = "writing stats response";
  return {
    project_id: stringField(item, "project_id", label),
    daily: arrayField(item, "daily", label, (entry, index) =>
      parseWordsRow(entry, "date", `${label}.daily[${index}]`),
    ),
    weekly: arrayField(item, "weekly", label, (entry, index) =>
      parseWordsRow(entry, "start_date", `${label}.weekly[${index}]`),
    ),
    streak_days: numberField(item, "streak_days", label),
    chapters: parseChapters(item.chapters, `${label}.chapters`),
    usage: parseStatsUsage(item.usage, `${label}.usage`),
  };
}

/** One daily (`date`) or weekly (`start_date`) attributed-words row. */
function parseWordsRow<K extends "date" | "start_date">(
  value: unknown,
  dateKey: K,
  label: string,
): K extends "date" ? WritingStatsDayRow : WritingStatsWeekRow {
  const item = objectValue(value, label);
  return {
    [dateKey]: stringField(item, dateKey, label),
    words: parseWords(item.words, `${label}.words`),
  } as K extends "date" ? WritingStatsDayRow : WritingStatsWeekRow;
}

function parseWords(value: unknown, label: string): WritingStatsWords {
  const item = objectValue(value, label);
  return {
    author: numberField(item, "author", label),
    ai_accepted: numberField(item, "ai_accepted", label),
    restore: numberField(item, "restore", label),
  };
}

function parseChapters(value: unknown, label: string): WritingStats["chapters"] {
  const item = objectValue(value, label);
  return {
    total: numberField(item, "total", label),
    started: numberField(item, "started", label),
  };
}

function parseStatsUsage(value: unknown, label: string): WritingStats["usage"] {
  const item = objectValue(value, label);
  const rowLabel = (name: string, index: number) => `${label}.${name}[${index}]`;
  return {
    project_id: stringField(item, "project_id", label),
    request_count: numberField(item, "request_count", label),
    prompt_tokens: numberField(item, "prompt_tokens", label),
    completion_tokens: numberField(item, "completion_tokens", label),
    per_model: arrayField(item, "per_model", label, (entry, index) => {
      const row = objectValue(entry, rowLabel("per_model", index));
      return {
        model: stringField(row, "model", rowLabel("per_model", index)),
        requests: numberField(row, "requests", rowLabel("per_model", index)),
        prompt_tokens: numberField(row, "prompt_tokens", rowLabel("per_model", index)),
        completion_tokens: numberField(row, "completion_tokens", rowLabel("per_model", index)),
      };
    }),
    daily: arrayField(item, "daily", label, (entry, index) => {
      const bucket = objectValue(entry, rowLabel("daily", index));
      return {
        date: stringField(bucket, "date", rowLabel("daily", index)),
        request_count: numberField(bucket, "request_count", rowLabel("daily", index)),
        prompt_tokens: numberField(bucket, "prompt_tokens", rowLabel("daily", index)),
        completion_tokens: numberField(bucket, "completion_tokens", rowLabel("daily", index)),
      };
    }),
  };
}
