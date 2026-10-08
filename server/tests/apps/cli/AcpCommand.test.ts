import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { PassThrough } from "node:stream";
import { expect, it } from "vitest";
import { runCli } from "../../../src/apps/cli/main.js";
import { AcpAgentProcess } from "../../../src/shared/infrastructure/acp/AcpAgentProcess.js";
import { AcpTokenFile } from "../../../src/shared/infrastructure/acp/AcpTokenFile.js";
import { AcpGateway } from "../../../src/shared/interface/acp/AcpGateway.js";

it("dispatches ACP connect through the single CLI without loading studio config and preserves repeated arguments", async () => {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-cli-"));
  const path = join(directory, "token");
  const token = await AcpTokenFile(path, { create: true });
  const script = join(directory, "agent.mjs");
  await writeFile(
    script,
    `import {createInterface} from 'node:readline';
for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:x.id,result:{args:process.argv.slice(2)}})+'\\n');}`,
  );
  const gateway = new AcpGateway({ token, launchAgent: AcpAgentProcess.launch });
  const input = new PassThrough();
  const output = new PassThrough();
  let received = "";
  output.on("data", (chunk) => {
    received += String(chunk);
  });
  try {
    const { url } = await gateway.listen({ port: 0 });
    const running = runCli(
      [
        "acp",
        "connect",
        "--url",
        url,
        "--token-file",
        path,
        "--command",
        process.execPath,
        "--arg",
        script,
        "--arg",
        "--acp",
        "--arg",
        "中文",
        "--cwd",
        directory,
      ],
      {
        envFile: join(directory, "must-not-load.env"),
        env: { APP_ENVIRONMENT: "invalid" },
        buildApplication: () => {
          throw new Error("ACP must not open the studio");
        },
        acp: { input, output },
      },
    );
    input.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}\n');
    await expect.poll(() => received).toContain('"args":["--acp","中文"]');
    input.end();
    expect(await running).toBe(0);
  } finally {
    input.destroy();
    output.destroy();
    await gateway.close();
    await rm(directory, { recursive: true, force: true });
  }
});
