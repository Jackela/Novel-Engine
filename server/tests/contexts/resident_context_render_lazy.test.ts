import { describe, expect, it } from "vitest";

import { iterateResidentContextSections } from "../../src/contexts/studio/application/resident_context.js";
import { PROJECT_OUTLINE_BEGIN } from "../../src/contexts/studio/application/sanitization.js";

describe("incremental resident prompt rendering", () => {
  it("never touches later sections after the consumer stops", () => {
    let priorTitleReads = 0;
    const iterator = iterateResidentContextSections({
      outline: { markdown: "# Outline\n\n## The Storm", linkedBeat: null },
      priorStory: [
        {
          ordinal: 1,
          get title() {
            priorTitleReads += 1;
            return "Later chapter";
          },
          digest: "Later digest.",
        },
      ],
      recentText: "Later tail.",
    });

    expect(iterator.next().value).toBe("");
    expect(iterator.next().value).toContain("OUTLINE");
    expect(iterator.next().value).toBe(PROJECT_OUTLINE_BEGIN);
    expect(iterator.next().value).toContain("The Storm");
    iterator.return(undefined);

    expect(priorTitleReads).toBe(0);
  });
});
