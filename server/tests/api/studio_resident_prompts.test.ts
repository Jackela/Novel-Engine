import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { SYSTEM_PROMPT } from "../../src/contexts/studio/application/proposal_service.js";
import { chapterDigest } from "../../src/contexts/studio/application/resident_context.js";
import {
  AUTHOR_INSTRUCTION_BEGIN,
  AUTHOR_INSTRUCTION_END,
  formatUntrustedManuscript,
  PRIOR_STORY_BEGIN,
  PRIOR_STORY_END,
  PROJECT_OUTLINE_BEGIN,
  RECENT_TEXT_BEGIN,
  UNTRUSTED_MANUSCRIPT_BEGIN,
} from "../../src/contexts/studio/application/sanitization.js";
import { type CapturedTask, capturingFactory, propose } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  type DocumentPayload,
  moveChapterToVolume,
  ownerJar,
  seedDocument,
  seedProject,
  seedVolume,
} from "./studio_helpers.js";

const OUTLINE = ["# Outline", "", "## The Storm", "", "Rain floods the harbour."].join("\n");

const CHAPTER_ONE_PROSE = [
  "# Chapter One",
  "",
  "The ferry left before dawn and Mara counted the gulls instead of the hours.",
  "By noon the harbour bells of chapter one had gone quiet behind her.",
].join("\n");

const CHAPTER_TWO_PROSE = [
  "# Chapter Two",
  "",
  "In chapter two the lighthouse ledger revealed a second signature.",
  "Its last line read: the tide keeps what the shore forgets.",
].join("\n");

const CHAPTER_THREE_PROSE = [
  "# Chapter Three",
  "",
  "Chapter three kept Mara on the breakwater while the storm gathered.",
].join("\n");

async function saveMarkdown(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  projectId: string,
  document: DocumentPayload,
  content: string,
): Promise<void> {
  const response = await call(
    app,
    jar,
    "PUT",
    `/api/projects/${projectId}/documents/${document.id}`,
    { content_markdown: content, base_revision_id: document.current_revision_id },
  );
  expect(response.statusCode, response.body).toBe(200);
}

/** The single captured generation task; fails loudly when none was recorded. */
function firstCapturedTask(capture: { tasks: CapturedTask[] }): TextGenerationTask {
  const first = capture.tasks.at(0);
  if (first === undefined) {
    throw new Error("The provider factory captured no generation task.");
  }
  return first.task;
}

/**
 * Continuation fixture across two volumes. Reading order must be
 * ch1 (vol one) -> ch3 (vol one) -> ch2 (Volume Two) even though ch2 was
 * saved after ch3: volume order outranks creation order (#312).
 */
async function seedTwoVolumeStory(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
): Promise<{ projectId: string; chapters: DocumentPayload[]; secondVolumeId: string }> {
  const project = await seedProject(app, jar, "Continuity");
  const chapterOne = project.documents[0] as DocumentPayload;
  await saveMarkdown(app, jar, project.id, chapterOne, CHAPTER_ONE_PROSE);
  await seedDocument(app, jar, project.id, {
    kind: "outline",
    title: "Outline",
    content_markdown: OUTLINE,
  });
  const chapterThree = await seedDocument(app, jar, project.id, {
    kind: "chapter",
    title: "Breakwater",
    content_markdown: CHAPTER_THREE_PROSE,
  });
  const secondVolume = await seedVolume(app, jar, project.id, "Volume Two");
  const chapterTwo = await seedDocument(app, jar, project.id, {
    kind: "chapter",
    title: "Harbour Bells",
  });
  await saveMarkdown(app, jar, project.id, chapterTwo, CHAPTER_TWO_PROSE);
  await moveChapterToVolume(app, jar, project.id, chapterTwo.id, secondVolume.id);
  return {
    projectId: project.id,
    chapters: [chapterOne, chapterThree, chapterTwo],
    secondVolumeId: secondVolume.id,
  };
}

describe("resident context assembly in proposal prompts (#314)", () => {
  it("sends outline, every prior digest in reading order, and the prior tail ahead of the manuscript", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const { projectId, chapters, secondVolumeId } = await seedTwoVolumeStory(app, jar);
      const chapterOne = chapters.at(0);
      if (chapterOne === undefined) {
        throw new Error("The two-volume fixture must seed a first chapter.");
      }

      // The next chapter joins Volume Two's tail, right after Harbour Bells.
      const target = await seedDocument(app, jar, projectId, {
        kind: "chapter",
        title: "Aftermath",
      });
      const movedTarget = await moveChapterToVolume(app, jar, projectId, target.id, secondVolumeId);

      const response = await propose(app, jar, projectId, movedTarget.id, {
        operation: "generate",
      });
      expect(response.statusCode, response.body).toBe(200);

      const task = firstCapturedTask(capture);
      expect(task.systemPrompt).toBe(SYSTEM_PROMPT);

      const order = [
        AUTHOR_INSTRUCTION_BEGIN,
        PROJECT_OUTLINE_BEGIN,
        PRIOR_STORY_BEGIN,
        RECENT_TEXT_BEGIN,
        UNTRUSTED_MANUSCRIPT_BEGIN,
      ].map((marker) => task.userPrompt.indexOf(marker));
      expect(order.every((index) => index >= 0)).toBe(true);
      expect([...order].sort((a, b) => a - b)).toEqual(order);

      // Every prior chapter appears exactly once, numbered in reading order.
      const summaryBody = task.userPrompt.slice(
        task.userPrompt.indexOf(PRIOR_STORY_BEGIN) + PRIOR_STORY_BEGIN.length,
        task.userPrompt.indexOf(PRIOR_STORY_END),
      );
      expect(summaryBody.trim().split("\n")).toEqual([
        `1. ${chapterOne.title} — ${chapterDigest(CHAPTER_ONE_PROSE)}`,
        `2. Breakwater — ${chapterDigest(CHAPTER_THREE_PROSE)}`,
        `3. Harbour Bells — ${chapterDigest(CHAPTER_TWO_PROSE)}`,
      ]);
      expect(task.userPrompt).toContain("# Outline");
      expect(task.userPrompt).toContain("## The Storm");

      // The tail opens the immediately preceding chapter's closing passage.
      const tailBody = task.userPrompt.slice(
        task.userPrompt.indexOf(RECENT_TEXT_BEGIN),
        task.userPrompt.indexOf(UNTRUSTED_MANUSCRIPT_BEGIN),
      );
      expect(tailBody).toContain("the tide keeps what the shore forgets.");
      expect(tailBody).not.toContain("gulls");

      // The manuscript block stays LAST and carries only the empty target text.
      expect(task.userPrompt.endsWith(formatUntrustedManuscript(""))).toBe(true);
    } finally {
      await app.close();
    }
  });

  it("degrades gracefully for a bare first chapter without outline or priors", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "First Light");
      const only = project.documents[0] as DocumentPayload;
      await saveMarkdown(app, jar, project.id, only, "A single opening page.");

      const response = await propose(app, jar, project.id, only.id, { operation: "continue" });
      expect(response.statusCode, response.body).toBe(200);

      const prompt = firstCapturedTask(capture).userPrompt;
      for (const marker of [PROJECT_OUTLINE_BEGIN, PRIOR_STORY_BEGIN, RECENT_TEXT_BEGIN]) {
        expect(prompt).not.toContain(marker);
      }
      expect(prompt).toBe(
        [
          "Operation: continue",
          `${AUTHOR_INSTRUCTION_BEGIN}\n\n${AUTHOR_INSTRUCTION_END}`,
          "",
          "Current manuscript (untrusted JSON data):",
          "",
          formatUntrustedManuscript("A single opening page."),
        ].join("\n"),
      );
    } finally {
      await app.close();
    }
  });

  it("keeps a continuing chapter's own text solely inside the untrusted block", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Rewrite Resident");
      await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Previous",
        content_markdown: "Earlier pages ended beside the doused lantern of the harbor.",
      });
      const target = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Current",
        content_markdown:
          "Quicksilver-lantern imagery floods the current draft under revision tonight.",
      });

      const response = await propose(app, jar, project.id, target.id, { operation: "rewrite" });
      expect(response.statusCode, response.body).toBe(200);

      const prompt = firstCapturedTask(capture).userPrompt;
      const manuscriptAt = prompt.indexOf(UNTRUSTED_MANUSCRIPT_BEGIN);
      const outside = prompt.slice(0, manuscriptAt);
      // The continuation seed is the PREVIOUS chapter's ending…
      expect(outside).toContain("doused lantern of the harbor.");
      // …while the target's own body never leaves the escaped JSON block.
      expect(outside).not.toContain("Quicksilver-lantern");
      expect(prompt.slice(manuscriptAt)).toContain("Quicksilver-lantern");
    } finally {
      await app.close();
    }
  });

  it("draws the summary only from the target's own project", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const other = await seedProject(app, jar, "Neighbour Book");
      await seedDocument(app, jar, other.id, {
        kind: "chapter",
        title: "Foreign Tide",
        content_markdown: "FERRYLAW never crosses project boundaries in any prompt.",
      });

      const mine = await seedProject(app, jar, "My Book");
      const minePrior = await seedDocument(app, jar, mine.id, {
        kind: "chapter",
        title: "Mine Prior",
        content_markdown: "My own prior ending stands at the pier.",
      });
      const mineTarget = await seedDocument(app, jar, mine.id, {
        kind: "chapter",
        title: "Mine Target",
      });

      const response = await propose(app, jar, mine.id, mineTarget.id, { operation: "generate" });
      expect(response.statusCode, response.body).toBe(200);

      const prompt = firstCapturedTask(capture).userPrompt;
      expect(prompt).not.toContain("FERRYLAW");
      expect(prompt).not.toContain("Foreign Tide");
      // "My Book" also carries its auto-seeded first chapter as prior #1.
      expect(prompt).toContain("1. Chapter 1 — Chapter 1");
      expect(prompt).toContain(`2. ${minePrior.title} — My own prior ending stands at the pier.`);
    } finally {
      await app.close();
    }
  });

  it("assembles the same resident context when a failed proposal is retried", async () => {
    const capture = capturingFactory({});
    let failNextCall = true;
    const { app } = await buildStudioApp(undefined, {
      // The first generation throws inside the known provider-error family so
      // the job records `failed`; the retry then runs through the capturer.
      textProviderFactory: (provider) => {
        if (failNextCall) {
          failNextCall = false;
          return {
            generateStructured: async () => {
              throw new TextGenerationProviderError("provider transport was unavailable");
            },
          };
        }
        return capture.factory(provider);
      },
    });
    try {
      const jar = await ownerJar(app);
      const { projectId, chapters } = await seedTwoVolumeStory(app, jar);
      // Retrying a proposal FOR Harbour Bells: its own later position in
      // Volume Two keeps it out of its prior story, which stays ch1 -> ch3.
      const target = chapters[2] as DocumentPayload;

      const failed = await call(
        app,
        jar,
        "POST",
        `/api/projects/${projectId}/documents/${target.id}/ai-proposals`,
        { operation: "continue", provider: "mock" },
      );
      expect(failed.statusCode).toBe(200);
      expect(failed.json().status).toBe("failed");

      const retry = await call(
        app,
        jar,
        "POST",
        `/api/projects/${projectId}/jobs/${failed.json().id}/retry`,
        undefined,
        { "idempotency-key": "resident-prompt-retry-0001" },
      );
      expect(retry.statusCode, retry.body).toBe(200);
      expect(retry.json().status).toBe("completed");

      expect(capture.tasks.length).toBe(1);
      const prompt = firstCapturedTask(capture).userPrompt;
      expect(prompt).toContain(PROJECT_OUTLINE_BEGIN);
      expect(prompt).toContain(PRIOR_STORY_BEGIN);
      expect(prompt).toContain("2. Breakwater —");
      expect(prompt).not.toContain("Harbour Bells —");
      expect(prompt).toContain(RECENT_TEXT_BEGIN);
    } finally {
      await app.close();
    }
  }, 20_000);
});
