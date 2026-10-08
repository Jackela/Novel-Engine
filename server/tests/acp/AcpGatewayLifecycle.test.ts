import { expect, it } from "vitest";
import { AcpAlive, AcpClosed, AcpHarness, AcpReply } from "./AcpHarness.js";

it("kills the whole agent process group when its connection closes", async () => {
  const harness =
    await AcpHarness(`const descendant=spawn(process.execPath,['-e','process.on("SIGTERM",()=>{});setInterval(()=>{},1000)'],{stdio:'ignore'});
process.on('SIGTERM',()=>{});
for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{parent:process.pid,descendant:descendant.pid}});}`);
  try {
    const socket = await harness.socket();
    const reply = AcpReply(socket);
    harness.initialize(socket);
    const result = (await reply).result as { parent: number; descendant: number };
    expect(AcpAlive(result.parent)).toBe(true);
    expect(AcpAlive(result.descendant)).toBe(true);
    socket.terminate();
    await harness.gateway.close();
    await expect.poll(() => AcpAlive(result.parent)).toBe(false);
    await expect.poll(() => AcpAlive(result.descendant)).toBe(false);
  } finally {
    await harness.close();
  }
});

it.each(["not-json\\n", "[]\\n"])(
  "closes and reaps an agent after invalid stdout: %s",
  async (output) => {
    const harness = await AcpHarness(
      `for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{pid:process.pid}});setTimeout(()=>process.stdout.write(${JSON.stringify(output.replaceAll("\\n", "\n"))}),50);}`,
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
