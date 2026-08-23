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

/** A provider factory that records every task it receives and returns fixed prose. */
export function capturingFactory(result: {
  markdown?: string;
  promptTokens?: number | null;
  completionTokens?: number | null;
}): { factory: TextGenerationProviderFactory; tasks: CapturedTask[] } {
  const tasks: CapturedTask[] = [];
  const factory: TextGenerationProviderFactory = (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async (task) => {
        tasks.push({ task, provider });
        return {
          step: task.step,
          provider,
          model: "captured-model",
          rawText: result.markdown ?? "captured raw text",
          content: { chapter_markdown: result.markdown ?? "" },
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
