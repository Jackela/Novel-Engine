import { expect, it } from "vitest";
import { AcpAlive, AcpClosed, AcpHarness, AcpReply } from "./AcpHarness.js";

it.each(["oversized", "invalid-utf8", "exit"])(
  "reaps an agent after stdout or process failure: %s",
  async (kind) => {
    const failure =
      kind === "oversized"
        ? "process.stdout.write('a'.repeat(1024*1024+1))"
        : kind === "invalid-utf8"
          ? "process.stdout.write(Buffer.from([0xc3,0x28,10]))"
          : "process.exit(7)";
    const harness = await AcpHarness(
      `for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{pid:process.pid}});setTimeout(()=>{${failure}},50);}`,
    );
    try {
      const socket = await harness.socket();
      const reply = AcpReply(socket);
      const closed = AcpClosed(socket);
      harness.initialize(socket);
      const result = (await reply).result as { pid: number };
      await closed;
      await harness.gateway.close();
      expect(AcpAlive(result.pid)).toBe(false);
    } finally {
      await harness.close();
    }
  },
);

it("bounds writes and kills the child when an agent stops consuming stdin", async () => {
  const harness = await AcpHarness(`const reader=createInterface({input:process.stdin});
reader.once('line',line=>{const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{pid:process.pid}});reader.close();process.stdin.pause();});setInterval(()=>{},1000);`);
  try {
    const socket = await harness.socket();
    const reply = AcpReply(socket);
    harness.initialize(socket);
    const result = (await reply).result as { pid: number };
    const closed = AcpClosed(socket);
    const frame = JSON.stringify({
      jsonrpc: "2.0",
      method: "session/prompt",
      params: { text: "a".repeat(900_000) },
    });
    for (let index = 0; index < 12; index += 1) socket.send(frame);
    await closed;
    await harness.gateway.close();
    expect(AcpAlive(result.pid)).toBe(false);
  } finally {
    await harness.close();
  }
});

it("redacts gateway credentials from bounded stderr and excludes them from the child environment", async () => {
  const harness = await AcpHarness(
    `for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{env:process.env.NE_TEST_ACP_TOKEN??null}});process.stderr.write('before __ACP_TEST_TOKEN__ after\\n');process.stderr.write('x'.repeat(20000));}`,
  );
  process.env.NE_TEST_ACP_TOKEN = harness.token;
  try {
    const socket = await harness.socket();
    const reply = AcpReply(socket);
    harness.initialize(socket);
    expect((await reply).result).toEqual({ env: null });
    await expect.poll(() => harness.diagnostics.length).toBe(2);
    expect(harness.diagnostics.join("\n")).not.toContain(harness.token);
    expect(harness.diagnostics[0]).toBe("before [redacted] after");
    expect(harness.diagnostics.join("\n").length).toBeLessThanOrEqual(16 * 1024);
  } finally {
    delete process.env.NE_TEST_ACP_TOKEN;
    await harness.close();
  }
});
