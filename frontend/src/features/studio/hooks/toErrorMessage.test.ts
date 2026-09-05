import { describe, expect, it } from "vitest";

import { HttpError } from "@/app/httpClient";

import { toErrorMessage } from "./toErrorMessage";

describe("toErrorMessage", () => {
  it("prefers the error's own message and falls back for non-errors", () => {
    expect(toErrorMessage(new Error("Unable to reach the studio."), "Fallback.")).toBe(
      "Unable to reach the studio.",
    );
    expect(toErrorMessage("a plain string", "Fallback.")).toBe("Fallback.");
    expect(toErrorMessage(undefined, "Fallback.")).toBe("Fallback.");
  });

  it("appends the refused resource and limit to a structure-capacity refusal", () => {
    const refusal = new HttpError(
      "Authoring structure capacity exceeded.",
      422,
      { resource: "project_volumes", limit: 100, observed: 101 },
      "STRUCTURE_CAPACITY_EXCEEDED",
    );
    expect(toErrorMessage(refusal, "Unable to create volume.")).toBe(
      "Authoring structure capacity exceeded. project_volumes limit is 100.",
    );
  });

  it("keeps other error semantics unchanged", () => {
    // A sibling capacity code with the same details shape stays untouched.
    const exportRefusal = new HttpError(
      "Export capacity exceeded.",
      422,
      { resource: "artifact_bytes", limit: 5242880, observed: 6000000 },
      "EXPORT_CAPACITY_EXCEEDED",
    );
    expect(toErrorMessage(exportRefusal, "Unable to export.")).toBe("Export capacity exceeded.");

    // The transport fallback still wins when the reason is not an Error.
    expect(toErrorMessage({ message: "shapeless" }, "Fallback.")).toBe("Fallback.");
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
      expect(toErrorMessage(refusal, "Fallback.")).toBe("Authoring structure capacity exceeded.");
    }
  });
});
