import { describe, expect, it } from "vitest";

import { sseDataPayloads } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";

const MIB = 1024 * 1024;

function byteStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

async function payloads(chunks: string[]): Promise<string[]> {
  const values: string[] = [];
  for await (const value of sseDataPayloads(byteStream(chunks))) values.push(value);
  return values;
}

describe("SSE mixed newline event boundaries", () => {
  it("recognizes every CRLF/LF combination across chunk boundaries without residual CR", async () => {
    const delimiters = ["\n\n", "\n\r\n", "\r\n\n", "\r\n\r\n"];
    const body = delimiters.map((delimiter, index) => `data: value-${index}${delimiter}`).join("");

    await expect(payloads([...body])).resolves.toEqual([
      "value-0",
      "value-1",
      "value-2",
      "value-3",
    ]);
  });

  it("accepts an event at exactly 1 MiB for a mixed delimiter", async () => {
    const shell = `data: ${JSON.stringify({ content: "" })}`;
    const rawEvent = `data: ${JSON.stringify({ content: "x".repeat(MIB - shell.length) })}`;
    expect(new TextEncoder().encode(rawEvent)).toHaveLength(MIB);

    const values = await payloads([rawEvent, "\n", "\r", "\n"]);

    expect(values).toHaveLength(1);
    expect(JSON.parse(values[0] ?? "{}")).toMatchObject({
      content: "x".repeat(MIB - shell.length),
    });
  });

  it("rejects an event one byte above 1 MiB for a mixed delimiter", async () => {
    const shell = `data: ${JSON.stringify({ content: "" })}`;
    const rawEvent = `data: ${JSON.stringify({ content: "x".repeat(MIB - shell.length + 1) })}`;
    expect(new TextEncoder().encode(rawEvent)).toHaveLength(MIB + 1);

    await expect(payloads([rawEvent, "\r", "\n", "\n"])).rejects.toThrow(
      /stream event exceeds 1 MiB limit/,
    );
  });
});
