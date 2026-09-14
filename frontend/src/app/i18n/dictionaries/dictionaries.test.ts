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
    } satisfies Partial<Record<MessageKey, string>>;
    for (const [key, expected] of Object.entries(anchors) as [MessageKey, string][]) {
      expect(en[key], key).toBe(expected);
    }
    // The compile-time type guarantees the anchor keys exist in zh too.
    const zhTyped: Dictionary = zh;
    expect(Object.keys(anchors).every((key) => key in zhTyped)).toBe(true);
  });
});
