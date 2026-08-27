import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  LOREBOOK_BEGIN,
  LOREBOOK_END,
  PROJECT_OUTLINE_BEGIN,
  UNTRUSTED_MANUSCRIPT_BEGIN,
} from "../../src/contexts/studio/application/sanitization.js";
import { type CapturedTask, capturingFactory, propose } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedDocument, seedProject } from "./studio_helpers.js";

const OUTLINE = ["# Outline", "", "Sable watches the flooded harbour."].join("\n");

/** The single captured generation task; fails loudly when none was recorded. */
function firstCapturedTask(capture: { tasks: CapturedTask[] }): TextGenerationTask {
  const first = capture.tasks.at(0);
  if (first === undefined) {
    throw new Error("The provider factory captured no generation task.");
  }
  return first.task;
}

describe("keyword-triggered lorebook in proposal prompts (#315)", () => {
  it("injects alias- and outline-triggered entries and omits the rest", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Lore Prompt");

      await seedDocument(app, jar, project.id, {
        kind: "outline",
        title: "Outline",
        content_markdown: OUTLINE,
      });
      // Alias-triggered: the manuscript names her epithet, not her title.
      const mara = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
        content_markdown: "Mara keeps the flooded archive beneath the Custom House.",
      });
      await call(app, jar, "PUT", `/api/projects/${project.id}/documents/${mara.id}/aliases`, {
        aliases: ["the archivist"],
      });
      // Title-triggered from the resident outline text alone.
      await seedDocument(app, jar, project.id, {
        kind: "world",
        title: "Sable",
        content_markdown: "Gull-winged pilot of the breakwater lights.",
      });
      // No key ever occurs: this entry must stay out of the prompt.
      await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Vantris",
        content_markdown: "A name no scene in this chapter will speak.",
      });
      const target = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Stacks",
        content_markdown: "She moved like the archivist through the stacks.",
      });

      const response = await propose(app, jar, project.id, target.id, {
        operation: "continue",
      });
      expect(response.statusCode, response.body).toBe(200);

      const prompt = firstCapturedTask(capture).userPrompt;
      expect(prompt).toContain("### Mara");
      expect(prompt).toContain("Mara keeps the flooded archive beneath the Custom House.");
      expect(prompt).toContain("### Sable");
      expect(prompt).toContain("Gull-winged pilot of the breakwater lights.");
      expect(prompt).not.toContain("### Vantris");
      expect(prompt).not.toContain("no scene in this chapter will speak");

      const order = [
        PROJECT_OUTLINE_BEGIN,
        LOREBOOK_BEGIN,
        LOREBOOK_END,
        UNTRUSTED_MANUSCRIPT_BEGIN,
      ].map((marker) => prompt.indexOf(marker));
      expect(order.every((index) => index >= 0)).toBe(true);
      expect([...order].sort((a, b) => a - b)).toEqual(order);
      // The manuscript block stays last and exactly once.
      expect(prompt.endsWith(prompt.slice(prompt.lastIndexOf(UNTRUSTED_MANUSCRIPT_BEGIN)))).toBe(
        true,
      );
    } finally {
      await app.close();
    }
  });

  it("adds no lore section for a plain chapter generation without lore docs", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "No Lore");
      const target = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Solo",
        content_markdown: "A single quiet page.",
      });

      const response = await propose(app, jar, project.id, target.id, { operation: "continue" });
      expect(response.statusCode, response.body).toBe(200);

      const prompt = firstCapturedTask(capture).userPrompt;
      for (const marker of [LOREBOOK_BEGIN, LOREBOOK_END]) {
        expect(prompt).not.toContain(marker);
      }
    } finally {
      await app.close();
    }
  });
});
