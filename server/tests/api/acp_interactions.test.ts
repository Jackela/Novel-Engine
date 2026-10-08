import { randomUUID } from "node:crypto";
import { rm } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";
import { fakeAcp, stop, textChunk } from "../contexts/acp_provider_fixture.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { authHeaders, buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

/** Read one public SSE event while preserving coalesced events between reads. */
function eventReader(response: Response) {
  const reader = response.body?.getReader();
  if (reader === undefined) throw new Error("Missing event body");
  let buffered = "";
  return {
    async next(): Promise<Record<string, unknown>> {
      for (;;) {
        const boundary = buffered.indexOf("\n\n");
        if (boundary >= 0) {
          const frame = buffered.slice(0, boundary);
          buffered = buffered.slice(boundary + 2);
          if (frame.startsWith("data: ")) return JSON.parse(frame.slice(6));
          continue;
        }
        const chunk = await reader.read();
        if (chunk.done) throw new Error("Event channel ended before expected event");
        buffered += new TextDecoder().decode(chunk.value);
      }
    },
    cancel: () => reader.cancel(),
  };
}

describe("ACP interaction API", () => {
  it("authorizes a project-bound permission, rejects duplicate/CSRF decisions, and replays the same Job without tool effects", async () => {
    const fixture = await fakeAcp((socket, message) => {
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 900,
          method: "session/request_permission",
          params: {
            sessionId: "session-1",
            toolCall: { toolCallId: "write-1", title: "Write material", kind: "edit" },
            options: [{ optionId: "allow", name: "Allow once", kind: "allow_once" }],
          },
        }),
      );
      const listener = (bytes: Buffer) => {
        const decision = JSON.parse(bytes.toString());
        if (decision.id !== 900 || decision.result === undefined) return;
        socket.off("message", listener);
        socket.send(
          JSON.stringify({
            jsonrpc: "2.0",
            method: "session/update",
            params: {
              sessionId: "session-1",
              update: {
                sessionUpdate: "tool_call",
                toolCallId: "write-1",
                title: "Write material",
                kind: "edit",
                status: "completed",
              },
            },
          }),
        );
        textChunk(socket, JSON.stringify({ chapter_markdown: validProposalProse }));
        stop(socket, message.id);
      };
      socket.on("message", listener);
    });
    const { app, directory } = await buildStudioApp(undefined, {
      textProviderFactory: (provider) =>
        provider === "acp"
          ? new AcpTextProvider(fixture.options)
          : new DeterministicStoryProvider(),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "ACP permissions");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Missing seed");
      const address = await app.listen({ host: "127.0.0.1", port: 0 });
      const operationId = randomUUID();
      const prefix = `/api/projects/${project.id}/ai-operations/${operationId}`;
      const anonymous = await app.inject({ method: "GET", url: `${prefix}/events` });
      expect(anonymous.statusCode).toBe(401);
      const events = eventReader(
        await fetch(`${address}${prefix}/events`, { headers: authHeaders(owner) }),
      );
      expect(await events.next()).toEqual({ type: "ready", operation_id: operationId });
      const headers = {
        "x-ai-operation-id": operationId,
        "idempotency-key": "acp-effects-once-0001",
      };
      const path = `/api/projects/${project.id}/documents/${document.id}/ai-proposals`;
      const pending = call(
        app,
        owner,
        "POST",
        path,
        { operation: "continue", provider: "acp" },
        headers,
      );
      const permission = await events.next();
      expect(permission.type).toBe("permission");
      const decisionPath = `${prefix}/permissions/${String(permission.permission_id)}`;
      const denied = await app.inject({
        method: "POST",
        url: decisionPath,
        headers: { cookie: authHeaders(owner).cookie },
        payload: { option_id: "allow" },
      });
      expect(denied.statusCode).toBe(403);
      const otherProject = await seedProject(app, owner, "Other scope");
      expect(
        (
          await call(app, owner, "POST", decisionPath.replace(project.id, otherProject.id), {
            option_id: "allow",
          })
        ).statusCode,
      ).toBe(422);
      expect(
        (await call(app, owner, "POST", decisionPath, { option_id: "allow" })).statusCode,
      ).toBe(204);
      const generated = await pending;
      expect(generated.statusCode, generated.body).toBe(200);
      expect(generated.json().status).toBe("completed");
      expect(generated.json().result.agent_execution).toMatchObject({
        operation_id: operationId,
        outcome_unknown: false,
        external_effects: [{ tool_id: "write-1", status: "completed" }],
      });
      expect(await events.next()).toMatchObject({ type: "tool", status: "completed" });
      expect(await events.next()).toEqual({ type: "completed", external_effects: "completed" });
      expect(
        (await call(app, owner, "POST", decisionPath, { option_id: "allow" })).statusCode,
      ).toBe(422);
      const replay = await call(
        app,
        owner,
        "POST",
        path,
        { operation: "continue", provider: "acp" },
        { "idempotency-key": headers["idempotency-key"] },
      );
      expect(replay.json().id).toBe(generated.json().id);
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
      await events.cancel();
    } finally {
      await app.close();
      await fixture.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
  it("executes all four provider steps through business APIs and streams started before manuscript deltas", async () => {
    const fixture = await fakeAcp((socket, message) => {
      const prompt = JSON.stringify(message.params);
      const content = prompt.includes("editorial_review")
        ? { findings: [] }
        : prompt.includes("lore_extract")
          ? { candidates: [] }
          : { chapter_markdown: validProposalProse };
      textChunk(socket, JSON.stringify(content));
      stop(socket, message.id);
    });
    const { app, directory } = await buildStudioApp(undefined, {
      textProviderFactory: (provider) =>
        provider === "acp"
          ? new AcpTextProvider(fixture.options)
          : new DeterministicStoryProvider(),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "ACP four steps");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Missing seed");
      const path = `/api/projects/${project.id}/documents/${document.id}/ai-proposals`;
      expect(
        (await call(app, owner, "POST", path, { operation: "generate", provider: "acp" })).json()
          .status,
      ).toBe("completed");
      const stream = await call(app, owner, "POST", `${path}/stream`, {
        operation: "rewrite",
        provider: "acp",
      });
      expect(stream.statusCode, stream.body).toBe(200);
      expect(JSON.parse(stream.body.split("\n\n")[0]?.slice(6) ?? "{}").type).toBe("started");
      expect(stream.body).toContain('"type":"done"');
      expect(
        (
          await call(app, owner, "PATCH", `/api/projects/${project.id}`, {
            settings: { provider: "acp" },
          })
        ).statusCode,
      ).toBe(200);
      const review = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`, {});
      expect(review.statusCode, review.body).toBe(201);
      expect(review.json().status).toBe("completed");
      const lore = await call(app, owner, "POST", `/api/projects/${project.id}/lore-extractions`, {
        provider: "acp",
        segment: "A visitor comes from the snow country.",
      });
      expect(lore.statusCode, lore.body).toBe(200);
      expect(lore.json().status).toBe("completed");
      expect(fixture.messages.filter((message) => message.method === "session/new")).toHaveLength(
        4,
      );
    } finally {
      await app.close();
      await fixture.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
  it("preserves unknown external effects on a failed Job after the observer disconnects", async () => {
    const fixture = await fakeAcp((socket) => {
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          method: "session/update",
          params: {
            sessionId: "session-1",
            update: {
              sessionUpdate: "tool_call",
              toolCallId: "write-unknown",
              title: "Write material",
              kind: "edit",
              status: "in_progress",
            },
          },
        }),
      );
    });
    const { app, directory } = await buildStudioApp(undefined, {
      textProviderFactory: () => new AcpTextProvider(fixture.options),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Unknown external effects");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Missing seed");
      const address = await app.listen({ host: "127.0.0.1", port: 0 });
      const operationId = randomUUID();
      const events = eventReader(
        await fetch(`${address}/api/projects/${project.id}/ai-operations/${operationId}/events`, {
          headers: authHeaders(owner),
        }),
      );
      await events.next();
      const pending = call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", provider: "acp" },
        { "x-ai-operation-id": operationId },
      );
      expect(await events.next()).toMatchObject({ type: "tool", status: "in_progress" });
      await events.cancel();
      const failed = await pending;
      expect(failed.statusCode, failed.body).toBe(200);
      expect(failed.json().status).toBe("failed");
      expect(failed.json().result.agent_execution).toMatchObject({
        operation_id: operationId,
        outcome_unknown: true,
        external_effects: [{ tool_id: "write-unknown", status: "in_progress" }],
      });
      const historic = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs/${failed.json().id}`,
      );
      expect(historic.json().result.agent_execution).toEqual(failed.json().result.agent_execution);
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
    } finally {
      await app.close();
      await fixture.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
