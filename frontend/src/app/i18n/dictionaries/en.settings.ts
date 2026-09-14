/** `settings.*` and `shell.*` screen messages. Merged into `en.ts`. */
export const enSettings = {
  "settings.heading": "Project settings",
  "settings.error.unableToUpdate": "Unable to update project.",
  "settings.field.provider": "Provider",
  "settings.field.storage": "Storage",
  "settings.field.documentSyntax": "Document syntax",
  "settings.value.sqlite": "SQLite",
  "settings.value.markdown": "Markdown",
  "settings.action.save": "Save settings",
  "settings.action.saving": "Saving…",
  "settings.status.saving": "Saving project settings.",

  "settings.diagnostics.privacy":
    "Diagnostics contains version, environment, configuration status, recent error summaries, and database health — nothing you wrote, no API keys. It is saved as a file on your computer; Novel Engine never sends it anywhere. Share it only if you choose to.",
  "settings.diagnostics.action.export": "Export diagnostics",
  "settings.diagnostics.action.exporting": "Exporting…",
  "settings.diagnostics.status.exporting": "Exporting diagnostics.",

  "shell.action.backToProjects": "Back to projects",
} as const;
