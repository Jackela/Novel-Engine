import { describe, expect, it } from "vitest";

import { type Dictionary, en, type MessageKey } from "./en";
import { zh } from "./zh";

/**
 * The dictionary contract, deliberately narrow (DR-038): key parity between
 * the languages, non-empty messages, and an anchor whitelist of the copy that
 * other tests locate by exact string. Plain copy edits outside the whitelist
 * need no test change; changing an anchored value MUST be mirrored in the
 * locating test in the same change.
 *
 * The whitelist is derived from usage, not from the dictionaries: every entry
 * exists because a Playwright spec in `frontend/tests/e2e-ts` (or a unit test
 * that matches rendered copy) locates that EN value. Do not pin copy merely
 * because it exists; add an entry together with the locating test, and delete
 * the entry when its last locating test goes away.
 */
describe("dictionaries", () => {
  it("keeps zh key parity with the English SSOT in both directions", () => {
    const enKeys = new Set(Object.keys(en));
    const zhKeys = new Set(Object.keys(zh));
    expect(
      Object.keys(zh).filter((key) => !enKeys.has(key)),
      "keys removed from en",
    ).toEqual([]);
    expect(
      Object.keys(en).filter((key) => !zhKeys.has(key)),
      "keys missing from zh",
    ).toEqual([]);
  });

  it("keeps every message a non-empty string in both languages", () => {
    for (const [name, dictionary] of [
      ["en", en],
      ["zh", zh],
    ] as const) {
      for (const [key, value] of Object.entries(dictionary)) {
        expect(typeof value === "string" && value.trim().length > 0, `${name}:${key}`).toBe(true);
      }
    }
  });

  it("keeps the EN anchors other tests locate by exact copy", () => {
    // Verified against `frontend/tests/e2e-ts` (Playwright locators) and the
    // unit tests that match rendered copy. Each entry below is load-bearing
    // for at least one locating test; orphaned pins are removed (DR-038).
    const anchors = {
      "common.action.tryAgain": "Try again",
      "entry.action.createOwner": "Create owner",
      "entry.action.signIn": "Sign in",
      "entry.field.password": "Password",
      "entry.field.username": "Username",
      "entry.heading.createOwner": "Create the local owner",
      "entry.heading.signedIn": "Open your writing studio",
      "library.action.create": "Create project",
      "library.action.signOut": "Sign out",
      "settings.action.save": "Save settings",
      "settings.action.saving": "Saving…",
      "shell.action.backToProjects": "Back to projects",
      "theme.option.dark": "Dark",
      "theme.option.systemDark": "System (dark)",

      // Studio workspace anchors (phase 2): the strings the Playwright
      // suite locates by role/text against the en-US locale. Templated
      // values are pinned in template form — the substitution contract
      // (params reproduce the pre-i18n literal byte-for-byte) is guarded
      // in `translate.test.ts` and the component i18n tests.
      "audit.action.generateAnother": "Generate another proposal",
      "beat.action.clear": "Clear",
      "beat.action.link": "Link beat",
      "beat.field.title": "Beat title",
      "copilot.action.accept": "Accept",
      "copilot.action.continue": "Continue",
      "copilot.field.instruction": "Proposal instruction",
      "copilot.placeholder.example": 'e.g. "Continue this scene with a quieter, more ominous tone"',
      "copilot.proposal.heading": "Proposed Markdown",
      "editor.action.retryDocument": "Retry document",
      "editor.conflict.action.keepLocal": "Keep local and retry overwrite",
      "editor.conflict.action.loadLatest": "Load latest (discard local)",
      "editor.empty": "Create a document to begin writing.",
      "editor.error.heading": "Unable to open this document",
      "editor.field.title": "Document title",
      "export.action.retry": "Retry {format} export",
      "export.history.empty": "No exports yet.",
      "export.history.end": "End of export history.",
      "export.history.heading": "Export history",
      "export.history.loadOlder": "Load older exports",
      "history.action.loadOlder": "Load older revisions",
      "history.heading": "Revision history",
      "history.status.allLoaded": "All revisions loaded",
      "inspector.tab.copilot": "Copilot",
      "inspector.tab.export": "Export",
      "inspector.tab.history": "History",
      "inspector.tab.jobs": "Jobs",
      "inspector.tab.review": "Review",
      "inspector.tab.stats": "Stats",
      "inspector.tab.usage": "Usage",
      "inspector.tablist": "Inspector panels",
      "navigator.group.add": "Add {group}",
      "navigator.group.characters": "Characters",
      "navigator.group.manuscript": "Manuscript",
      "navigator.group.outline": "Outline",
      "navigator.row.confirmBody": "Permanently delete {title}? Unsaved changes are lost.",
      "navigator.row.confirmHeading": "Delete {title} confirmation",
      "navigator.row.confirmDelete": "Confirm delete {title}",
      "navigator.row.moveDown": "Move {title} down",
      "navigator.row.moveToVolume": "Move to volume…",
      "navigator.row.movingUp": "Moving {title} up",
      "navigator.row.moveUp": "Move {title} up",
      "navigator.row.placeVolume": "Place {title} in volume",
      "navigator.search.label": "Search project",
      "navigator.search.results": "Search results",
      "navigator.section.manuscript": "Manuscript",
      "navigator.section.settings": "Settings",
      "review.empty": "No review findings. Run a review when ready.",
      "review.heading": "Review findings",
      "review.status.loadingHistory": "Loading review history…",
      "usage.action.refresh": "Refresh usage",
      "usage.daily.region": "Daily usage, last 30 days",
      "usage.empty": "No usage recorded yet.",
      "usage.table.label": "Usage per model",
      "wholeBook.action.generateEmpty": "Generate the {count} empty {unit} only",
      "wholeBook.action.replaceOccupied": "Replace the {count} {unit} with AI drafts",
      "wholeBook.action.start": "Generate whole book",
      "wholeBook.action.stop": "Stop generating",
      "wholeBook.confirm.listLabel": "Chapters that would be replaced",
      "wholeBook.status.generating": "Generating chapter {current} of {total}…",
    } satisfies Partial<Record<MessageKey, string>>;
    for (const [key, expected] of Object.entries(anchors) as [MessageKey, string][]) {
      expect(en[key], key).toBe(expected);
    }
    // The compile-time type guarantees the anchor keys exist in zh too.
    const zhTyped: Dictionary = zh;
    expect(Object.keys(anchors).every((key) => key in zhTyped)).toBe(true);
  });

  it("keeps the EN count-unit nouns the templated anchors interpolate", () => {
    // The e2e suite matches composed strings such as "Stopped — 2 chapters
    // accepted" and "{count} words" — the units the call sites interpolate
    // are anchors in their own right.
    expect(en["noun.chapters"]).toBe("chapters");
    expect(en["noun.words"]).toBe("words");
  });
});
