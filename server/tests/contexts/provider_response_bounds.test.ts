import { describe, expect, it } from "vitest";

import type { TextGenerationStreamOptions } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { ProviderTransportError } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { responseJsonObject } from "../../src/contexts/ai/infrastructure/providers/provider_json.js";
import type { StreamingTextRequest } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { streamProviderTextDeltas } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";

const MIB = 1024 * 1024;

function streamRequest(): StreamingTextRequest {
  return {
    url: "https://provider.example/v1/chat/completions",
    headers: {},
    body: "{}",
    signal: undefined,
    context: "bounded provider stream",
    timeoutSeconds: 30,
    model: "bounded-model",
  };
}

function bodyFromChunks(chunks: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk);
      controller.close();
    },
  });
}

function responseFromChunks(chunks: Uint8Array[]): Response {
  return new Response(bodyFromChunks(chunks), {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

function extractDelta(chunk: Record<string, unknown>): string | undefined {
  return typeof chunk.content === "string" ? chunk.content : undefined;
}

function extractUsage(): readonly [number | null, number | null] {
  return [null, null];
}

async function consume(
  transport: ProviderTransport,
  options?: TextGenerationStreamOptions,
  extractor = extractDelta,
): Promise<string[]> {
  const deltas: string[] = [];
  for await (const delta of streamProviderTextDeltas(
    streamRequest(),
    transport,
    extractor,
    extractUsage,
    options,
  )) {
    deltas.push(delta);
  }
  return deltas;
}

describe("bounded synchronous provider bodies", () => {
  it("rejects a JSON response above 8 MiB without cloning the original response", async () => {
    const response = responseFromChunks([new Uint8Array(8 * MIB + 1)]);
    let cloneCalls = 0;
    Object.defineProperty(response, "clone", {
      value: () => {
        cloneCalls += 1;
        throw new Error("the untrusted response must not be cloned");
      },
    });

    await expect(responseJsonObject(response, "bounded sync response")).rejects.toThrow(
      /response body exceeds 8 MiB limit/,
    );
    expect(cloneCalls).toBe(0);
  });

  it("sanitizes a synchronous body-read TypeError without exposing diagnostics", async () => {
    const diagnostic = "credential-in-sync-reader";
    let reads = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        reads += 1;
        if (reads === 1) {
          controller.enqueue(new TextEncoder().encode("{"));
          return;
        }
        controller.error(new TypeError(`socket closed near ${diagnostic}`));
      },
    });
    const landed = await responseJsonObject(new Response(body), "bounded sync response").catch(
      (error: unknown) => error,
    );

    expect(landed).toBeInstanceOf(ProviderTransportError);
    expect((landed as Error).message).not.toContain(diagnostic);
  });
});

describe("bounded SSE provider bodies", () => {
  it("rejects one event above 1 MiB and aborts the upstream signal", async () => {
    const event = `data: ${JSON.stringify({ content: "x".repeat(MIB) })}\n\n`;
    let signal: AbortSignal | undefined;
    const transport: ProviderTransport = (_url, init) => {
      signal = init?.signal ?? undefined;
      return Promise.resolve(responseFromChunks([new TextEncoder().encode(event)]));
    };

    await expect(consume(transport)).rejects.toThrow(/stream event exceeds 1 MiB limit/);
    expect(signal?.aborted).toBe(true);
  });

  it("rejects a total SSE response above 8 MiB before reporting an outcome", async () => {
    const event = `data: ${JSON.stringify({ content: "x".repeat(950_000) })}\n\n`;
    const body = new TextEncoder().encode(event.repeat(9));
    let outcome = false;

    await expect(
      consume(() => Promise.resolve(responseFromChunks([body])), {
        onOutcome: () => {
          outcome = true;
        },
      }),
    ).rejects.toThrow(/response body exceeds 8 MiB limit/);
    expect(outcome).toBe(false);
  });

  it("sanitizes a TypeError raised only by the body-read boundary", async () => {
    const credential = "upstream-secret-in-reader";
    let reads = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        reads += 1;
        if (reads === 1) {
          controller.enqueue(
            new TextEncoder().encode(`data: ${JSON.stringify({ content: "safe" })}\n\n`),
          );
          return;
        }
        controller.error(new TypeError(`socket failed with ${credential}`));
      },
    });
    const failure = consume(() => Promise.resolve(new Response(body, { status: 200 })));
    const landed = await failure.catch((error: unknown) => error);

    expect(landed).toBeInstanceOf(ProviderTransportError);
    expect((landed as Error).message).not.toContain(credential);
  });

  it("does not disguise extractor TypeErrors as transport failures", async () => {
    const programmingError = new TypeError("extractor implementation defect");
    const event = `data: ${JSON.stringify({ content: "safe" })}\n\n`;
    const failure = consume(
      () => Promise.resolve(responseFromChunks([new TextEncoder().encode(event)])),
      undefined,
      () => {
        throw programmingError;
      },
    );

    await expect(failure).rejects.toBe(programmingError);
  });
});
