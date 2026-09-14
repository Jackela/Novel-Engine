import type { Dictionary } from "./en";
import { zhEntry } from "./zh.entry";
import { zhErrors } from "./zh.errors";
import { zhLibrary } from "./zh.library";
import { zhSettings } from "./zh.settings";
import { zhShared } from "./zh.shared";
import { zhStudio } from "./zh.studio";

/**
 * Simplified-Chinese dictionary, merged from the per-screen chunks that
 * mirror `en.*.ts`. The `Dictionary` annotation makes a missing or
 * misspelled key a compile error, so `zh` can never silently drift from the
 * English key set. Proper nouns the product already treats as opaque
 * (Markdown, SQLite, DashScope, API key, Copilot) keep their Latin form.
 */
export const zh: Dictionary = {
  ...zhShared,
  ...zhEntry,
  ...zhLibrary,
  ...zhSettings,
  ...zhStudio,
  ...zhErrors,
};
