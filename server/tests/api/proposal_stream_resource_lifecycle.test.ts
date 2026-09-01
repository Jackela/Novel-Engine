import { Agent, request as httpRequest } from "node:http";
import type { Socket } from "node:net";

import { describe, expect, it } from "vitest";
import { authHeaders, buildStudioApp, ownerJar, seedProject } from "./studio_helpers.js";

function postJson(
  address: string,
  path: string,
  agent: Agent,
  headers: Record<string, string>,
  payload: Record<string, unknown>,
): Promise<{ statusCode: number; body: string }> {
  const body = JSON.stringify(payload);
  return new Promise((resolve, reject) => {
    const request = httpRequest(
      new URL(path, address),
      {
        method: "POST",
        agent,
        headers: {
          ...headers,
          "content-type": "application/json",
          "content-length": Buffer.byteLength(body),
        },
      },
      (response) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk: Buffer) => chunks.push(chunk));
        response.once("end", () => {
          resolve({
            statusCode: response.statusCode ?? 0,
            body: Buffer.concat(chunks).toString("utf8"),
          });
        });
      },
    );
    request.once("error", reject);
    request.end(body);
  });
}

describe("proposal stream resource lifecycle", () => {
  it("detaches disconnect listeners after each completed keep-alive request", async () => {
    const { app } = await buildStudioApp();
    const sockets: Socket[] = [];
    app.server.on("connection", (socket) => sockets.push(socket));
    const owner = await ownerJar(app);
    const project = await seedProject(app, owner, "Keep-alive stream lifecycle");
    const document = project.documents[0];
    if (document === undefined) throw new Error("Expected the seeded chapter.");
    const agent = new Agent({ keepAlive: true, maxSockets: 1 });
    try {
      const address = await app.listen({ host: "127.0.0.1", port: 0 });
      const path = `/api/projects/${project.id}/documents/${document.id}/ai-proposals/stream`;
      let baselineCloseListeners = -1;
      for (let index = 0; index < 14; index += 1) {
        const response = await postJson(address, path, agent, authHeaders(owner), {
          operation: "continue",
          provider: "mock",
        });
        expect(response.statusCode, response.body).toBe(200);
        expect(response.body).toContain('"type":"done"');
        await new Promise<void>((resolve) => setImmediate(resolve));
        expect(sockets).toHaveLength(1);
        if (index === 0) baselineCloseListeners = sockets[0]?.listenerCount("close") ?? -1;
      }

      expect(baselineCloseListeners).toBeGreaterThanOrEqual(0);
      expect(sockets[0]?.listenerCount("close")).toBe(baselineCloseListeners);
    } finally {
      agent.destroy();
      await app.close();
    }
  });
});
