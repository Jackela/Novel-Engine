import { rm } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { fakeAcp, stop, textChunk } from "../contexts/acp_provider_fixture.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

describe("ACP external effect evidence capacity", () => {
  it("refuses success rather than silently dropping the 101st unknown action", async () => {
    const fixture = await fakeAcp((socket, message) => {
      for (let index = 0; index < 101; index += 1)
        socket.send(
          JSON.stringify({
            jsonrpc: "2.0",
            method: "session/update",
            params: {
              sessionId: "session-1",
              update: {
                sessionUpdate: "tool_call",
                toolCallId: `tool-${index}`,
                title: "Synthetic action",
                kind: "edit",
                status: index === 100 ? "in_progress" : "completed",
              },
            },
          }),
        );
      textChunk(socket, JSON.stringify({ chapter_markdown: validProposalProse }));
      stop(socket, message.id);
    });
    const { app, directory } = await buildStudioApp(undefined, {
      textProviderFactory: () => new AcpTextProvider(fixture.options),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Bounded tool evidence");
      const document = project.documents.find((entry) => entry.kind === "chapter");
      if (document === undefined) throw new Error("Missing chapter");
      const response = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { provider: "acp", operation: "continue" },
      );
      expect(response.statusCode, response.body).toBe(200);
      const failed = response.json();
      expect(failed.status).toBe("failed");
      expect(failed.error).toContain("evidence limit");
      expect(failed.result.agent_execution.external_effects).toHaveLength(100);
      expect(failed.result.agent_execution.outcome_unknown).toBe(true);
      const historic = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs/${failed.id}`,
      );
      expect(historic.json().result.agent_execution).toEqual(failed.result.agent_execution);
      expect(fixture.messages.filter((entry) => entry.method === "session/prompt")).toHaveLength(1);
    } finally {
      await app.close();
      await fixture.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
