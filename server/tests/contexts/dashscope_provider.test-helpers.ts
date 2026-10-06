import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { fixtureApiKey } from "../credential_fixtures.js";

/** Fixtures and transports shared by the DashScope adapter test files. */
export interface CapturedRequest {
  url: string;
  init: RequestInit;
}

export const DASHSCOPE_ORIGIN = "https://dashscope.aliyuncs.com";
export const NATIVE_GENERATION_PATH_SEGMENTS = [
  "api",
  "v1",
  "services",
  "aigc",
  "multimodal-generation",
  "generation",
] as const;
/** Official OpenAI-compatible Responses path (#502): default base plus endpoint suffix. */
export const RESPONSES_DEFAULT_PATH_SEGMENTS = ["compatible-mode", "v1", "responses"] as const;

export function expectedEndpoint(origin: string, pathSegments: readonly string[]): string {
  return new URL(pathSegments.join("/"), `${origin}/`).toString();
}

export function chapterTask(step: string): TextGenerationTask {
  return {
    step,
    systemPrompt: "system prompt",
    userPrompt: "user prompt",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2 },
  };
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export function generationBody(
  content: unknown,
  usage?: Record<string, number>,
): Record<string, unknown> {
  return {
    output: { choices: [{ message: { content } }] },
    usage: usage ?? { prompt_tokens: 11, completion_tokens: 22 },
  };
}

/** Records every request and answers from a script (Response or Error); optional per-call behavior. */
export function scriptedTransport(
  script: Array<Response | Error | (() => Response | Error)>,
  capture: CapturedRequest[],
): ProviderTransport {
  let call = 0;
  return (url, init) => {
    capture.push({ url: String(url), init: init ?? {} });
    const scripted = script[Math.min(call, script.length - 1)];
    call += 1;
    const answer = typeof scripted === "function" ? scripted() : scripted;
    if (answer instanceof Error) {
      return Promise.reject(answer);
    }
    return Promise.resolve(answer);
  };
}

export function provider(
  overrides: Partial<ConstructorParameters<typeof DashScopeTextProvider>[0]> = {},
) {
  return new DashScopeTextProvider({
    apiKey: fixtureApiKey("sk-dashscope", "test"),
    model: "qwen3.5-flash",
    retry: { maxAttempts: 3, delayMs: 1000, sleep: async () => {} },
    ...overrides,
  });
}
