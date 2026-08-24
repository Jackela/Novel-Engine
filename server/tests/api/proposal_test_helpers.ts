import type { FastifyInstance } from "fastify";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { type CookieJar, call } from "./studio_helpers.js";

export interface CapturedTask {
  task: TextGenerationTask;
  provider: string;
}

/** Narrative fixture that satisfies the completed-proposal content contract. */
export const validProposalProse = [
  "At dawn, Mara found the archive corridor open for the first time in winter. Dust lay in pale ribbons across the stone, but one set of fresh boot prints crossed it and stopped beside the map cabinet. She listened at the locked door beyond the shelves until the house settled around her.",
  "Inside the cabinet, the river chart had been folded beneath a ledger of vanished ferries. Mara traced the inked route with one finger and saw that the final crossing ended at the old bell tower, not at the harbor shown on every public map. Someone had changed the story of the road on purpose.",
  "She copied the date into her notebook, then heard a page turn in the reading room. The sound was careful enough to be a warning. Rather than run, Mara tucked the chart beneath her coat and walked toward the doorway, rehearsing the harmless question she would ask if anyone challenged her.",
  "The morning light reached the tiles as she emerged, thin and gold. It showed her a wet line leading from the reading room to the garden gate. Mara followed it into the cold, carrying the chart close to her ribs and knowing that the next choice would belong to her alone.",
].join("\n\n");

/** A provider factory that records every task it receives and returns fixed prose. */
export function capturingFactory(result: {
  markdown?: string;
  chapterMarkdown?: string | null;
  promptTokens?: number | null;
  completionTokens?: number | null;
}): { factory: TextGenerationProviderFactory; tasks: CapturedTask[] } {
  const tasks: CapturedTask[] = [];
  const factory: TextGenerationProviderFactory = (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async (task) => {
        tasks.push({ task, provider });
        const markdown = result.markdown ?? validProposalProse;
        const chapterMarkdown = Object.hasOwn(result, "chapterMarkdown")
          ? result.chapterMarkdown
          : markdown;
        return {
          step: task.step,
          provider,
          model: "captured-model",
          rawText: markdown,
          content: { chapter_markdown: chapterMarkdown },
          promptTokens: result.promptTokens ?? null,
          completionTokens: result.completionTokens ?? null,
        };
      },
    };
    return impl;
  };
  return { factory, tasks };
}

/** POST the proposal endpoint without asserting a status. */
export function propose(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  body: Record<string, unknown>,
) {
  return call(
    app,
    jar,
    "POST",
    `/api/projects/${projectId}/documents/${documentId}/ai-proposals`,
    body,
  );
}
