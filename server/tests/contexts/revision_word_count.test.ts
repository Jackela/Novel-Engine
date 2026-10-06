import { describe, expect, it } from "vitest";

import {
  documentPayload,
  revisionPayload,
} from "../../src/contexts/studio/application/payloads.js";
import {
  RevisionWordCountInvariantError,
  revisionWordCount,
} from "../../src/contexts/studio/domain/revision_word_count.js";

describe("revision word count", () => {
  it.each([
    ["hello world", 2],
    ["don't state-of-the-art", 2],
    ["123 45_6", 2],
    ["", 0],
    ["a\uD800b", 2],
  ])("preserves the established Unicode word-run result for %j", (markdown, expected) => {
    expect(revisionWordCount(markdown)).toBe(expected);
  });

  it.each([
    ["天地玄黄宇宙洪荒日月盈昃辰宿列张寒来暑往秋收冬藏闰余成岁律吕调", 31],
    ["你好世界", 4],
    ["hello，世界！", 3],
    ["他走进房间。窗外下着雨。", 10],
    ["你好 world", 3],
    ["a好b", 3],
  ])(
    "counts Han characters individually and sums them with word runs for %j",
    (markdown, expected) => {
      expect(revisionWordCount(markdown)).toBe(expected);
    },
  );

  it.each([null, -1, 1.5, Number.NaN, Number.MAX_SAFE_INTEGER + 1])(
    "refuses invalid stored evidence %s",
    (wordCount) => {
      const createdAt = new Date("2026-09-03T00:00:00.000Z");
      const revision = {
        id: "revision-1",
        documentId: "document-1",
        parentRevisionId: null,
        revisionNumber: 1,
        contentMarkdown: "one two",
        metadataJson: "{}",
        source: "author",
        wordCount,
        createdAt,
      };
      expect(() => revisionPayload(revision)).toThrow(RevisionWordCountInvariantError);
      expect(() =>
        documentPayload({
          id: "document-1",
          projectId: "project-1",
          kind: "chapter",
          title: "Chapter",
          position: 1,
          volumeId: "volume-1",
          beatRef: null,
          loreAliasesJson: "[]",
          loreStatus: "draft",
          currentRevisionId: revision.id,
          createdAt,
          updatedAt: createdAt,
          currentRevision: revision,
        }),
      ).toThrow(RevisionWordCountInvariantError);
    },
  );
});
