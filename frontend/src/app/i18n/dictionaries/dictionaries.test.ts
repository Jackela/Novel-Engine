import { describe, expect, it } from "vitest";

import { type Dictionary, en, type MessageKey } from "./en";
import { zh } from "./zh";

/**
 * Runtime guard for what the compiler already enforces (`zh: Dictionary`)
 * plus the e2e anchor contract: the Playwright suite locates the EN strings
 * byte-exactly, so any intentional EN value change here must be mirrored in
 * frontend/tests/e2e-ts specs in the same change.
 */
describe("dictionaries", () => {
  it("keeps zh key-complete against the English SSOT", () => {
    expect(Object.keys(zh).sort()).toEqual(Object.keys(en).sort());
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

  it("keeps the EN anchors the e2e suite locates by byte-stable", () => {
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
      "library.status.loading": "Loading projects...",
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
      "export.formats.legend": "Export formats",
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
      "wholeBook.action.start": "Generate whole book",
      "wholeBook.action.stop": "Stop generating",
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
