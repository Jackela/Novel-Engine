import { randomBytes } from "node:crypto";
import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { PassThrough } from "node:stream";
import { expect, it } from "vitest";
import { AcpAgentProcess } from "../../src/shared/infrastructure/acp/AcpAgentProcess.js";
import { AcpConnect } from "../../src/shared/interface/acp/AcpConnect.js";
import { AcpGateway } from "../../src/shared/interface/acp/AcpGateway.js";
import { AcpHarness } from "./AcpHarness.js";

it("bridges stdio permission requests, responses, updates, and cancellation without filtering methods", async () => {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-connect-"));
  const script = join(directory, "agent.mjs");
  await writeFile(
    script,
    `import {createInterface} from 'node:readline';
const send=x=>process.stdout.write(JSON.stringify(x)+'\\n');
for await(const line of createInterface({input:process.stdin})){
const x=JSON.parse(line);
if(x.method==='initialize') send({jsonrpc:'2.0',id:x.id,result:{protocolVersion:1}});
else if(x.method==='session/prompt') send({jsonrpc:'2.0',id:'permission',method:'session/request_permission',params:{sessionId:'s',options:[{optionId:'yes',kind:'allow_once',name:'Proceed'}]}});
else if(x.id==='permission') send({jsonrpc:'2.0',method:'session/update',params:{sessionId:'s',update:{sessionUpdate:'agent_message_chunk',content:{type:'text',text:'中文'}}}});
else if(x.method==='session/cancel') send({jsonrpc:'2.0',method:'observed',params:x});
}`,
  );
  const token = randomBytes(32).toString("base64url");
  const gateway = new AcpGateway({ token, launchAgent: AcpAgentProcess.launch });
  const input = new PassThrough();
  const output = new PassThrough();
  let received = "";
  output.on("data", (chunk) => {
    received += String(chunk);
  });
  try {
    const { url } = await gateway.listen({ port: 0 });
    const connecting = AcpConnect({
      url,
      token,
      launch: { command: process.execPath, args: [script], cwd: directory },
      input,
      output,
    });
    input.write(
      `${JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: { protocolVersion: 1 },
      })}\n`,
    );
    await expect.poll(() => received).toContain('"protocolVersion":1');
    input.write('{"jsonrpc":"2.0","id":2,"method":"session/prompt","params":{}}\n');
    await expect.poll(() => received).toContain('"method":"session/request_permission"');
    input.write(
      '{"jsonrpc":"2.0","id":"permission","result":{"outcome":{"outcome":"selected","optionId":"yes"}}}\n',
    );
    await expect.poll(() => received).toContain('"text":"中文"');
    input.write('{"jsonrpc":"2.0","method":"session/cancel","params":{"sessionId":"s"}}\n');
    await expect.poll(() => received).toContain('"method":"observed"');
    input.end();
    expect(await connecting).toBe(0);
    expect(
      received
        .split("\n")
        .filter(Boolean)
        .map((line) => JSON.parse(line).jsonrpc),
    ).toEqual(["2.0", "2.0", "2.0", "2.0"]);
  } finally {
    input.destroy();
    output.destroy();
    await gateway.close();
    await rm(directory, { recursive: true, force: true });
  }
});

it("closes normally when stdin reached EOF before the WebSocket handshake", async () => {
  const harness = await AcpHarness("setInterval(()=>{},1000);");
  const input = new PassThrough();
  const output = new PassThrough();
  const ended = once(input, "end");
  input.end();
  input.resume();
  await ended;
  try {
    const connecting = AcpConnect({
      url: harness.url,
      token: harness.token,
      launch: { command: process.execPath, args: [harness.script], cwd: harness.directory },
      input,
      output,
    });
    expect(
      await Promise.race([
        connecting,
        new Promise<string>((resolve) => setTimeout(() => resolve("timeout"), 250)),
      ]),
    ).toBe(0);
  } finally {
    input.destroy();
    output.destroy();
    await harness.close();
  }
});
