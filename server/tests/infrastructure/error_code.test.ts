import { describe, expect, it } from "vitest";

import { errorCode as studioErrorCode } from "../../src/contexts/studio/infrastructure/export_artifact_fs_support.js";
import { errorCode } from "../../src/shared/infrastructure/error_code.js";

describe("errorCode", () => {
  it("returns the string code of an errno-style error", () => {
    expect(errorCode({ code: "ENOENT" })).toBe("ENOENT");
  });

  it("returns undefined for a non-string code instead of coercing it", () => {
    expect(errorCode({ code: 13 })).toBeUndefined();
  });

  it("returns undefined when the error carries no code property", () => {
    expect(errorCode({})).toBeUndefined();
  });

  it("returns undefined for null and primitive thrown values", () => {
    expect(errorCode(null)).toBeUndefined();
    expect(errorCode(undefined)).toBeUndefined();
    expect(errorCode("ENOENT")).toBeUndefined();
  });

  it("is the single definition reused across studio and db infrastructure", () => {
    expect(studioErrorCode).toBe(errorCode);
  });
});
