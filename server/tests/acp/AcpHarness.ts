import { randomBytes } from "node:crypto";
import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import WebSocket from "ws";
import { AcpAgentProcess } from "../../src/shared/infrastructure/acp/AcpAgentProcess.js";
import { AcpGateway } from "../../src/shared/interface/acp/AcpGateway.js";

/** Exercise an authenticated real WebSocket against a real subprocess in an isolated directory. */
export async function AcpHarness(body: string) {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-boundary-"));
  const script = join(directory, "agent.mjs");
  const token = randomBytes(32).toString("base64url");
  await writeFile(
    script,
    `import {createInterface} from 'node:readline';
import {spawn} from 'node:child_process';
const send=x=>process.stdout.write(JSON.stringify(x)+'\\n');
${body.replaceAll("__ACP_TEST_TOKEN__", token)}`,
  );
  const diagnostics: string[] = [];
  const gateway = new AcpGateway({
    token,
    launchAgent: AcpAgentProcess.launch,
    diagnostic: (message) => diagnostics.push(message),
  });
  const { url } = await gateway.listen({ port: 0 });
  const sockets: WebSocket[] = [];
  return {
    token,
    directory,
    script,
    gateway,
    url,
    diagnostics,
    async socket() {
      const socket = new WebSocket(url, { headers: { authorization: `Bearer ${token}` } });
      sockets.push(socket);
      await once(socket, "open");
      return socket;
    },
    initialize(socket: WebSocket, overrides: Record<string, unknown> = {}) {
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: 1,
            _meta: {
              "novel-engine/acp-proxy": {
                command: process.execPath,
                args: [script],
                cwd: directory,
                ...overrides,
              },
            },
          },
        }),
      );
    },
    async close() {
      for (const socket of sockets) socket.terminate();
      await gateway.close();
      await rm(directory, { recursive: true, force: true });
    },
  };
}

export async function AcpReply(socket: WebSocket): Promise<Record<string, unknown>> {
  const [raw] = await once(socket, "message");
  return JSON.parse(String(raw));
}

export function AcpClosed(socket: WebSocket): Promise<number> {
  return new Promise((resolve) => {
    socket.once("close", resolve);
    socket.on("error", () => undefined);
  });
}

export function AcpAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (error instanceof Error && "code" in error && error.code === "ESRCH") return false;
    throw error;
  }
}
