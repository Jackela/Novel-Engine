import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { PassThrough } from "node:stream";
import { expect, it } from "vitest";
import WebSocket from "ws";
import { runCli } from "../../../src/apps/cli/main.js";
import type {
  ShutdownSignalHandler,
  ShutdownSignalSource,
} from "../../../src/apps/cli/shutdown_signals.js";
import { AcpTokenFile } from "../../../src/shared/infrastructure/acp/AcpTokenFile.js";
import { AcpAlive, AcpHarness, AcpReply } from "../../acp/AcpHarness.js";

function signals() {
  const handlers = new Map<string, ShutdownSignalHandler>();
  const source: ShutdownSignalSource = {
    add: (signal, handler) => {
      handlers.set(signal, handler);
    },
    remove: (signal) => {
      handlers.delete(signal);
    },
  };
  return { handlers, source };
}

it("serves independently and SIGTERM drains the child, socket, and signal handlers", async () => {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-serve-"));
  const reserve = createServer();
  reserve.listen(0, "127.0.0.1");
  await once(reserve, "listening");
  const address = reserve.address();
  if (!address || typeof address === "string") throw new Error("Missing test port.");
  await new Promise<void>((resolve, reject) =>
    reserve.close((error) => (error ? reject(error) : resolve())),
  );
  const path = join(directory, "token");
  const script = join(directory, "agent.mjs");
  await writeFile(
    script,
    `import {createInterface} from 'node:readline';for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:x.id,result:{pid:process.pid}})+'\\n');}`,
  );
  const latch = signals();
  const diagnostics: string[] = [];
  const running = runCli(["acp", "serve", "--token-file", path, "--port", String(address.port)], {
    env: { APP_ENVIRONMENT: "invalid" },
    shutdownSignalSource: latch.source,
    writeLine: (line) => diagnostics.push(line),
  });
  let socket: WebSocket | undefined;
  try {
    await expect
      .poll(() => diagnostics.some((line) => line.startsWith("ACP gateway listening")))
      .toBe(true);
    const token = await AcpTokenFile(path);
    socket = new WebSocket(`ws://127.0.0.1:${address.port}/acp`, {
      headers: { authorization: `Bearer ${token}` },
    });
    await once(socket, "open");
    const reply = AcpReply(socket);
    socket.send(
      JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: 1,
          _meta: {
            "novel-engine/acp-proxy": { command: process.execPath, args: [script], cwd: directory },
          },
        },
      }),
    );
    const result = (await reply).result as { pid: number };
    latch.handlers.get("SIGTERM")?.();
    expect(await running).toBe(143);
    expect(AcpAlive(result.pid)).toBe(false);
    expect(latch.handlers.size).toBe(0);
    expect(diagnostics.join("\n")).not.toContain(token);
  } finally {
    latch.handlers.get("SIGTERM")?.();
    await running;
    socket?.terminate();
    await rm(directory, { recursive: true, force: true });
  }
});

it("connect SIGTERM closes its exclusive agent and removes signal handlers", async () => {
  const harness = await AcpHarness(
    `for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{pid:process.pid}});}`,
  );
  const tokenPath = join(harness.directory, "token");
  await writeFile(tokenPath, harness.token, { mode: 0o600 });
  const input = new PassThrough();
  const output = new PassThrough();
  const latch = signals();
  let received = "";
  output.on("data", (chunk) => {
    received += String(chunk);
  });
  const running = runCli(
    [
      "acp",
      "connect",
      "--url",
      harness.url,
      "--token-file",
      tokenPath,
      "--command",
      process.execPath,
      "--arg",
      harness.script,
      "--cwd",
      harness.directory,
    ],
    { acp: { input, output }, shutdownSignalSource: latch.source },
  );
  try {
    input.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}\n');
    await expect.poll(() => received).toContain('"pid":');
    const pid = JSON.parse(received.trim()).result.pid;
    latch.handlers.get("SIGTERM")?.();
    expect(await running).toBe(143);
    await harness.gateway.close();
    expect(AcpAlive(pid)).toBe(false);
    expect(latch.handlers.size).toBe(0);
  } finally {
    latch.handlers.get("SIGTERM")?.();
    await running;
    input.destroy();
    output.destroy();
    await harness.close();
  }
});
