import { describe, expect, it } from "vitest";

import {
  decodeRevisionCursor,
  encodeRevisionCursor,
} from "../../src/contexts/studio/interface/http/revision_cursor.js";

describe("revision pagination cursor contract", () => {
  it("round-trips only canonical project-and-document-bound cursor positions", () => {
    const position = { revisionNumber: 27, id: "revision-a" };
    const token = encodeRevisionCursor("project-a", "document-a", position);
    expect(token).not.toBeNull();
    expect(decodeRevisionCursor(token ?? "", "project-a", "document-a")).toEqual(position);

    const encoded = (json: string) => Buffer.from(json, "utf8").toString("base64url");
    const invalidTokens = [
      "not+base64url",
      `${token}=`,
      ` ${token}`,
      Buffer.from([0xff]).toString("base64url"),
      (token ?? "").slice(0, -1),
      encoded('[1,"project-a","document-a",27,"revision-a"'),
      encoded('[2,"project-a","document-a",27,"revision-a"]'),
      encoded('[1,"project-a","document-a",0,"revision-a"]'),
      encoded('[1,"project-a","document-a",-1,"revision-a"]'),
      encoded('[1,"project-a","document-a",1.5,"revision-a"]'),
      encoded('[1,"project-a","document-a",9007199254740992,"revision-a"]'),
      encoded('[1,"project-a","document-a",27,""]'),
      encoded(`[1,"project-a","document-a",27,"${"x".repeat(129)}"]`),
      encoded('[1,"project-a","document-a",27,"revision-a","extra"]'),
      encoded('[1, "project-a","document-a",27,"revision-a"]'),
      encoded('[1,"project\\u002da","document-a",27,"revision-a"]'),
      encoded('[1,"project-a","document-a",2.7e1,"revision-a"]'),
    ];
    for (const invalid of invalidTokens) {
      expect(() => decodeRevisionCursor(invalid, "project-a", "document-a")).toThrowError(
        expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
      );
    }
    expect(() => decodeRevisionCursor(token ?? "", "project-b", "document-a")).toThrowError(
      expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
    );
    expect(() => decodeRevisionCursor(token ?? "", "project-a", "document-b")).toThrowError(
      expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
    );
  });
});
