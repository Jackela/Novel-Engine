import { describe, expect, it } from "vitest";

import { HttpError } from "@/app/httpClient";
import { setActiveLanguage } from "@/app/i18n/language";
import { localizeError } from "@/app/localizeError";

import { toErrorMessage } from "./toErrorMessage";

describe("toErrorMessage", () => {
  it("prefers the error's own message and falls back for non-errors", () => {
    expect(toErrorMessage(new Error("Unable to reach the studio."), "Fallback.")).toBe(
      "Unable to reach the studio.",
    );
    // An uncoded transport failure keeps its own (client-owned) message.
    expect(toErrorMessage(new HttpError("Sign in required.", 401), "Fallback.")).toBe(
      "Sign in required.",
    );
    expect(toErrorMessage("a plain string", "Fallback.")).toBe("Fallback.");
    expect(toErrorMessage(undefined, "Fallback.")).toBe("Fallback.");
  });

  it("localizes a coded envelope instead of echoing the server's English prose", () => {
    const refusal = new HttpError(
      "Authoring structure capacity exceeded: project_volumes limit 100.",
      422,
      { resource: "project_volumes", limit: 100, observed: 101 },
      "STRUCTURE_CAPACITY_EXCEEDED",
    );
    expect(toErrorMessage(refusal, "Unable to create volume.")).toBe(
      "The volume count reached its limit (100). Remove some structure before retrying.",
    );
  });

  it("resolves the message against the active language", () => {
    setActiveLanguage("zh");
    try {
      const unauthorized = new HttpError("Owner session required.", 401, undefined, "UNAUTHORIZED");
      expect(toErrorMessage(unauthorized, "无法继续。")).toBe("登录状态已过期，请重新登录后继续。");
    } finally {
      setActiveLanguage("en");
    }
  });

  it("maps sibling capacity codes without leaking the raw resource identifier", () => {
    const exportRefusal = new HttpError(
      "Export capacity exceeded: artifact_bytes limit 5242880.",
      422,
      { resource: "artifact_bytes", limit: 5242880, observed: 6000000 },
      "EXPORT_CAPACITY_EXCEEDED",
    );
    const message = toErrorMessage(exportRefusal, "Unable to export.");
    expect(message).toBe(
      "The export exceeds the allowed export size (limit 5242880). Reduce the export and retry.",
    );
    expect(message).not.toContain("artifact_bytes");

    const payloadRefusal = new HttpError("Request body is too large", 413, undefined, undefined);
    expect(toErrorMessage(payloadRefusal, "Fallback.")).toBe(
      "This chapter is too large to save. Split it into smaller chapters — your draft stays in the editor.",
    );
  });

  it("ignores malformed capacity details instead of guessing", () => {
    const cases: Array<unknown> = [
      { resource: "project_volumes", limit: "many" },
      { resource: "", limit: 100 },
      { limit: 100 },
      null,
    ];
    for (const details of cases) {
      const refusal = new HttpError(
        "Authoring structure capacity exceeded.",
        422,
        details,
        "STRUCTURE_CAPACITY_EXCEEDED",
      );
      const message = toErrorMessage(refusal, "Fallback.");
      expect(message).toBe(
        "This change would exceed the project's structure limit. Remove some structure before retrying.",
      );
      expect(message).not.toContain("{resource}");
      expect(message).not.toContain("{limit}");
    }
  });

  it("withholds the provider's raw report from the primary message but keeps it as technical detail", () => {
    const raw =
      "DashScope generation failed for step 'chapter_revision': provider returned HTTP 401.";
    const providerFailure = new HttpError(raw, 502, undefined, "PROVIDER_FAILED");

    const primary = toErrorMessage(providerFailure, "Unable to create proposal.");
    expect(primary).toBe(
      "The AI provider request failed (HTTP 401). Check the provider configuration and retry.",
    );
    expect(primary).not.toContain("provider returned HTTP");

    // The raw report stays available for the technical-details affordance.
    expect(localizeError(providerFailure, "Unable to create proposal.").technical).toBe(raw);
  });

  it("keeps an unknown code visible as a localized generic message", () => {
    const unknown = new HttpError("Kernel panic.", 500, undefined, "SOMETHING_NEW");
    expect(toErrorMessage(unknown, "Fallback.")).toBe(
      "The request failed (SOMETHING_NEW). Retry; if it persists, report this code.",
    );
  });
});
