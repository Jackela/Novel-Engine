/**
 * English dictionary — the SSOT for the message-key family. Every key a
 * component may request is declared as a literal in one of the per-screen
 * chunks merged below, so `Dictionary` (and therefore `MessageKey`) is
 * derived from this object: requesting an unknown key is a compile error,
 * and `zh.ts` must provide every key before it type-checks. English is the
 * default language, so these values are also the exact strings the e2e
 * suite locates against — edit them only together with the matching e2e
 * specs (see `dictionaries.test.ts` for the pinned anchors).
 *
 * Key families (phase-2 convention): two or three segments —
 * `<screen>.<group>.<camelCaseLeaf>` per screen/panel, plus the shared
 * `common.*`, `theme.*`, `language.*`, `provider.*`, and `noun.*` families.
 * The two-segment form is legal wherever a group would add nothing
 * (`theme.legend`, `library.intro`, `settings.heading`, every
 * `provider.*` key). Values may carry `{name}` placeholders resolved by
 * `translate`; substituting the current parameters must reproduce the
 * pre-i18n literal byte-for-byte.
 *
 * File layout: when the flat dictionary outgrew the file-size budget, the
 * values moved to per-screen chunks (`en.shared.ts`, `en.entry.ts`,
 * `en.library.ts`, `en.settings.ts`, `en.studio.ts`, `en.errors.ts`) that
 * this file re-merges and types; each `zh.*.ts` chunk mirrors one chunk.
 */

import { enEntry } from "./en.entry";
import { enErrors } from "./en.errors";
import { enLibrary } from "./en.library";
import { enSettings } from "./en.settings";
import { enShared } from "./en.shared";
import { enStudio } from "./en.studio";

export const en = {
  ...enShared,
  ...enEntry,
  ...enLibrary,
  ...enSettings,
  ...enStudio,
  ...enErrors,
} as const;

/**
 * The canonical key set every dictionary must satisfy. Keys stay literal
 * (an unknown key never type-checks) while values widen to `string`, so
 * translations hold different text under the same keys.
 */
export type Dictionary = Record<keyof typeof en, string>;

/**
 * One per-screen slice of a dictionary: keys must belong to the canonical
 * set, but coverage is partial — the merged `zh` in `zh.ts` is annotated
 * with the full `Dictionary`, which is what keeps the chunks collectively
 * key-complete.
 */
export type DictionaryChunk = Partial<Dictionary>;

/** Any key the active dictionary resolves; unknown keys fail to compile. */
export type MessageKey = keyof Dictionary;

/**
 * Placeholder values for `{name}` slots in a message template. Numbers are
 * formatted by the caller (the dictionaries never reformat counts), so the
 * substitution itself is a pure `String()` cast.
 */
export type MessageParams = Readonly<Record<string, string | number>>;
