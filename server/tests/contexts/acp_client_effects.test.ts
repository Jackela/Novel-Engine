import { readFile, realpath, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { AcpWorkspace } from "../../src/contexts/ai/infrastructure/providers/AcpWorkspace.js";
import { validProposalProse } from "../api/proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "../api/studio_helpers.js";
import { fakeAcp, stop, textChunk } from "./acp_provider_fixture.js";

describe("client-owned ACP file effect evidence", () => {
  it.each([false, true])(
    "persists a delegated write without agent tool notifications (partial failure: %s)",
    async (partialFailure) => {
      let materialPath = "";
      const fixture = await fakeAcp((socket, message) => {
        socket.send(
          JSON.stringify({
            jsonrpc: "2.0",
            id: 900,
            method: "fs/write_text_file",
            params: { sessionId: "session-1", path: materialPath, content: "edited material" },
          }),
        );
        const onWrite = (bytes: Buffer) => {
          const response = JSON.parse(bytes.toString());
          if (response.id !== 900) return;
          socket.off("message", onWrite);
          textChunk(socket, JSON.stringify({ chapter_markdown: validProposalProse }));
          stop(socket, message.id);
        };
        socket.on("message", onWrite);
      });
      materialPath = join(await realpath(fixture.options.workspaceRoot ?? ""), "material.md");
      await writeFile(materialPath, "original material");
      const fault = partialFailure
        ? vi.spyOn(AcpWorkspace.prototype, "write").mockImplementation(async () => {
            await writeFile(materialPath, "partial");
            throw new Error("Synthetic I/O failure after a partial write");
          })
        : undefined;
      const { app, directory } = await buildStudioApp(undefined, {
        textProviderFactory: () => new AcpTextProvider(fixture.options),
      });
      try {
        const owner = await ownerJar(app);
        const project = await seedProject(app, owner, "Client file effects");
        const document = project.documents[0];
        if (document === undefined) throw new Error("Missing seed document");
        const response = await call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue", provider: "acp" },
        );
        expect(response.statusCode, response.body).toBe(200);
        const job = response.json();
        expect(job.status).toBe("completed");
        expect(await readFile(materialPath, "utf8")).toBe(
          partialFailure ? "partial" : "edited material",
        );
        expect(job.result.agent_execution).toMatchObject({
          outcome_unknown: partialFailure,
          external_effects: [
            {
              tool_id: expect.stringMatching(/^novel-engine:client-write:/u),
              title: "Write material file",
              kind: "edit",
              status: partialFailure ? "unknown" : "completed",
              target: "material.md",
            },
          ],
        });
        expect(JSON.stringify(job.result.agent_execution)).not.toContain("edited material");
        const stored = await call(app, owner, "GET", `/api/projects/${project.id}/jobs/${job.id}`);
        expect(stored.json().result.agent_execution).toEqual(job.result.agent_execution);
        expect(
          fixture.messages.filter((message) => message.method === "session/prompt"),
        ).toHaveLength(1);
      } finally {
        fault?.mockRestore();
        await app.close();
        await fixture.close();
        await rm(directory, { recursive: true, force: true });
      }
    },
  );
});
