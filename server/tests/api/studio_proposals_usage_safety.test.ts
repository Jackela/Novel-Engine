import { describe, expect, it } from "vitest";

import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import { usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { capturingFactory, propose, validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, ownerJar, seedProject } from "./studio_helpers.js";

describe("proposal usage safe-integer normalization", () => {
  it("falls back when an injected synchronous provider reports unsafe token counts", async () => {
    const capture = capturingFactory({
      markdown: validProposalProse,
      promptTokens: Number.MAX_SAFE_INTEGER + 1,
      completionTokens: 1e308,
    });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Unsafe counts");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const instruction = "Tighten this scene safely.";

      await propose(app, jar, project.id, document.id, {
        operation: "continue",
        instruction,
      });

      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected studio database handle");
      const usageEvent = db.select().from(usageEvents).get();
      if (usageEvent === undefined) throw new Error("expected usage event");
      expect(usageEvent.prompt_tokens).toBe(wordCount(instruction));
      expect(usageEvent.completion_tokens).toBe(wordCount(validProposalProse));
    } finally {
      await app.close();
    }
  });
});
