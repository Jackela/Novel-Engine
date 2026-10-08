import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { type VerifyClientCallbackAsync, type WebSocket, WebSocketServer } from "ws";
import type { AcpProviderOptions } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
export interface FakeAcpMessage {
  id?: number;
  method?: string;
  params?: Record<string, unknown>;
  result?: unknown;
}
/** Public protocol fixture with a real authenticated WebSocket boundary. */
export async function fakeAcp(
  prompt: (socket: WebSocket, message: FakeAcpMessage) => void,
): Promise<{ options: AcpProviderOptions; messages: FakeAcpMessage[]; close(): Promise<void> }> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-fake-acp-"));
  const tokenFile = join(directory, "proxy-token");
  await writeFile(tokenFile, "test-proxy-token");
  const messages: FakeAcpMessage[] = [];
  const server = new WebSocketServer({
    port: 0,
    host: "127.0.0.1",
    verifyClient: ((info, done) =>
      done(
        info.req.headers.authorization === "Bearer test-proxy-token",
      )) satisfies VerifyClientCallbackAsync,
  });
  await once(server, "listening");
  server.on("connection", (socket) =>
    socket.on("message", (bytes) => {
      const message: FakeAcpMessage = JSON.parse(bytes.toString());
      messages.push(message);
      const reply = (result: unknown) =>
        socket.send(JSON.stringify({ jsonrpc: "2.0", id: message.id, result }));
      if (message.method === "initialize")
        reply({
          protocolVersion: 1,
          agentCapabilities: {},
          authMethods: [{ id: "cached_token", name: "Cached" }],
        });
      else if (message.method === "authenticate") reply({});
      else if (message.method === "session/new")
        reply({
          sessionId: "session-1",
          configOptions: [
            {
              id: "model",
              name: "Model",
              category: "model",
              type: "select",
              currentValue: "fake-model",
              options: [{ value: "fake-model", name: "Fake model" }],
            },
          ],
        });
      else if (message.method === "session/prompt") prompt(socket, message);
    }),
  );
  const address = server.address();
  if (address === null || typeof address === "string") throw new Error("Expected socket address");
  return {
    options: {
      proxyUrl: `ws://127.0.0.1:${address.port}/acp`,
      tokenFile,
      command: "fake",
      args: [],
      workspaceRoot: directory,
      handshakeMs: 500,
      executionMs: 500,
      overallMs: 2000,
    },
    messages,
    close: async () => {
      for (const socket of server.clients) socket.terminate();
      await new Promise<void>((resolve) => server.close(() => resolve()));
      await rm(directory, { recursive: true, force: true });
    },
  };
}
export function textChunk(socket: WebSocket, text: string): void {
  socket.send(
    JSON.stringify({
      jsonrpc: "2.0",
      method: "session/update",
      params: {
        sessionId: "session-1",
        update: { sessionUpdate: "agent_message_chunk", content: { type: "text", text } },
      },
    }),
  );
}
export function stop(socket: WebSocket, id: number | undefined, reason = "end_turn"): void {
  socket.send(JSON.stringify({ jsonrpc: "2.0", id, result: { stopReason: reason } }));
}
