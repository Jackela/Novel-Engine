import { describe, expect, it } from "vitest";

import { isProposalMarkdownProse } from "../../src/contexts/studio/application/sanitization.js";
import {
  buildStudioApp,
  draftProposal,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

/**
 * DR-023 end-to-end: a project whose captured content is Chinese drives a
 * Chinese chapter from the deterministic mock and lands the same completed
 * job shape; an English project keeps the English prompt and prose.
 */

const CHINESE_MANUSCRIPT = [
  "她推开门时，雨声灌满了整条走廊。灯在风里摇晃，像有人举着它犹豫不决。",
  "远处传来钟声，一下又一下，把夜色敲得更薄。她把信折好，放进外套的内袋，听见脚步在楼梯上停了一拍。",
].join("\n\n");

describe("proposal generation follows the project writing language (DR-023)", () => {
  it("generates Chinese prose for a Chinese project through the mock provider", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "雪国纪事");
      const chapter = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "第一章 初雪",
        content_markdown: CHINESE_MANUSCRIPT,
      });

      const job = await draftProposal(app, jar, project.id, chapter.id, {
        operation: "generate",
        instruction: "续写这一章。",
        provider: "mock",
      });

      expect(job.status).toBe("completed");
      const proposal = job.result.proposal_markdown as string;
      expect(proposal).toContain("第2章");
      expect(proposal).toContain("第一章 初雪");
      expect(proposal).toMatch(/[\u3400-\u9fff]/u);
      expect(isProposalMarkdownProse(proposal)).toBe(true);
    } finally {
      await app.close();
    }
  });

  it("keeps English prose for an English project", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "English project");
      const document = project.documents[0];
      if (document === undefined) throw new Error("seedProject must create a document.");

      const job = await draftProposal(app, jar, project.id, document.id, {
        operation: "generate",
        instruction: "",
        provider: "mock",
      });

      expect(job.status).toBe("completed");
      expect(job.result.proposal_markdown).toContain("Chapter 1");
    } finally {
      await app.close();
    }
  });
});
