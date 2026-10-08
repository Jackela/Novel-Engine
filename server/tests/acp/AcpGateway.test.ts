import { randomBytes } from "node:crypto";
import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";
import WebSocket from "ws";
import { AcpAgentProcess } from "../../src/shared/infrastructure/acp/AcpAgentProcess.js";
import { AcpGateway } from "../../src/shared/interface/acp/AcpGateway.js";

it("launches one real agent and forwards initialize without the proxy metadata", async () => {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-gateway-"));
  const script = join(directory, "agent.mjs");
  await writeFile(
    script,
    `import {createInterface} from 'node:readline';
for await (const line of createInterface({input:process.stdin})) {
const message=JSON.parse(line); process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:message.id,result:{echo:message,args:process.argv.slice(2)}})+'\\n');
}`,
  );
  const token = randomBytes(32).toString("base64url");
  const gateway = new AcpGateway({ token, launchAgent: AcpAgentProcess.launch });
  let socket: WebSocket | undefined;
  try {
    const address = await gateway.listen({ port: 0 });
    socket = new WebSocket(address.url, { headers: { authorization: `Bearer ${token}` } });
    await once(socket, "open");
    const reply = once(socket, "message");
    socket.send(
      JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: 1,
          clientCapabilities: { fs: { readTextFile: true } },
          _meta: {
            "novel-engine/acp-proxy": {
              command: process.execPath,
              args: [script, "中文"],
              cwd: directory,
            },
            future: { retained: true },
          },
        },
      }),
    );
    const [raw] = await reply;
    const result = JSON.parse(String(raw));
    expect(result.result.echo).toEqual({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: 1,
        clientCapabilities: { fs: { readTextFile: true } },
        _meta: { future: { retained: true } },
      },
    });
    expect(result.result.args).toEqual(["中文"]);
  } finally {
    socket?.terminate();
    await gateway.close();
    await rm(directory, { recursive: true, force: true });
  }
});
