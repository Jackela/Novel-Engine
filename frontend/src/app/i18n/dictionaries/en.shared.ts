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
  "provider.acp": "Grok (ACP)",
  "acp.action.viewActivity": "View tool activity",
  "acp.error.evidence": "Unable to load tool activity. Retry after the details are available.",
  "acp.effects.none": "No file changes were recorded.",
  "acp.retry.confirmation": "Confirm retry after checking files",
  "acp.retry.warning":
    "Your material files may have changed. Check the working folder before retrying.",
  "acp.retry.confirm": "I checked the working folder; retry",
  "acp.retry.cancel": "Cancel",
  "acp.heading": "Agent tools",
  "acp.status.running": "Working…",
  "acp.status.connecting": "Connecting…",
  "acp.status.waiting": "Waiting for your decision",
  "acp.status.completed": "Operation completed",
  "acp.status.error": "Operation failed",
  "acp.status.cancelled": "Operation stopped",
  "acp.action.stop": "Stop operation",
  "acp.effects.completed": "Completed file changes remain in your working folder.",
  "acp.effects.unknown":
    "Review your working folder before running this operation again; file changes may have completed.",
  "acp.error.observationLost":
    "Tool observation ended unexpectedly. Review your working folder before trying again.",
  "acp.error.missingObserver": "Reconnect to the project before using ACP.",
  "acp.error.permission": "Unable to send your decision. Try again while the request is active.",
  "settings.provider.acpNotConfigured": "not configured (ACP connection)",
  "settings.provider.acpMissingConnection":
    "The server ACP connection is not configured. Configure the connection and restart, or choose another provider.",

  // Count units pick their leaf at the call site (`count === 1 ? ... : ...`)
  // so templates stay word-order free; Chinese uses one form for both.
  "noun.chapter": "chapter",
  "noun.chapters": "chapters",
  "noun.finding": "finding",
  "noun.findings": "findings",
  "noun.word": "word",
  "noun.words": "words",
} as const;
