/**
 * Shared message families: `common.*`, `theme.*`, `language.*`,
 * `provider.*`, and the `noun.*` count units. Merged into the canonical
 * dictionary in `en.ts`; edit EN values only together with the matching
 * e2e specs (see `dictionaries.test.ts`).
 */
export const enShared = {
  "common.action.tryAgain": "Try again",
  "common.action.tryingAgain": "Trying again...",
  "common.action.saving": "Saving…",
  "common.field.title": "Title",
  "common.field.description": "Description",

  "theme.legend": "Theme",
  "theme.option.system": "System",
  "theme.option.systemLight": "System (light)",
  "theme.option.systemDark": "System (dark)",
  "theme.option.light": "Light",
  "theme.option.dark": "Dark",

  // Option labels are native names shown in their own language on purpose:
  // a reader who cannot parse the active language must still find theirs.
  "language.legend": "Language",
  "language.option.en": "English",
  "language.option.zh": "中文",

  "provider.mock": "Mock (trial — no API key)",
  "provider.dashscope": "DashScope",
  "provider.openaiCompatible": "OpenAI-compatible",

  // Count units pick their leaf at the call site (`count === 1 ? ... : ...`)
  // so templates stay word-order free; Chinese uses one form for both.
  "noun.chapter": "chapter",
  "noun.chapters": "chapters",
  "noun.finding": "finding",
  "noun.findings": "findings",
  "noun.word": "word",
  "noun.words": "words",
} as const;
