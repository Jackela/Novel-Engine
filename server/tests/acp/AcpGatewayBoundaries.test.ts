import { expect, it } from "vitest";
import WebSocket from "ws";
import { AcpAlive, AcpClosed, AcpHarness, AcpReply } from "./AcpHarness.js";

it.each(["anonymous", "wrong-token", "browser"])(
  "rejects unauthenticated or browser-origin HTTP upgrades: %s",
  async (kind) => {
    const harness = await AcpHarness("setInterval(()=>{},1000);");
    try {
      const status = new Promise<number>((resolve) => {
        const socket = new WebSocket(harness.url, {
          ...(kind === "anonymous"
            ? {}
            : {
                headers: {
                  authorization: `Bearer ${kind === "browser" ? harness.token : "wrong"}`,
                },
              }),
          ...(kind === "browser" ? { origin: "https://browser.example" } : {}),
        });
        socket.on("unexpected-response", (_request, response) => {
          resolve(response.statusCode ?? 0);
          response.resume();
          socket.terminate();
        });
        socket.on("error", () => undefined);
      });
      expect(await status).toBe(401);
    } finally {
      await harness.close();
    }
  },
);

it.each([
  { command: "./agent" },
  { cwd: "relative" },
  { cwd: "/path-that-does-not-exist/ne-acp" },
  { env: { TOKEN: "client-env" } },
])("refuses invalid launch descriptors before forwarding initialize: %j", async (override) => {
  const harness = await AcpHarness("setInterval(()=>{},1000);");
  try {
    const socket = await harness.socket();
    const closed = AcpClosed(socket);
    harness.initialize(socket, override);
    await closed;
  } finally {
    await harness.close();
  }
});

it.each(["{broken", "null", "[]", '{"jsonrpc":"2.0","method":"session/new","params":{}}'])(
  "closes invalid or uninitialized clients: %s",
  async (text) => {
    const harness = await AcpHarness("setInterval(()=>{},1000);");
    try {
      const socket = await harness.socket();
      const closed = AcpClosed(socket);
      socket.send(text);
      await closed;
    } finally {
      await harness.close();
    }
  },
);

it.each(["oversized", "binary", "utf8"])(
  "closes and reaps the child on invalid WS framing: %s",
  async (kind) => {
    const harness = await AcpHarness(
      `for await(const line of createInterface({input:process.stdin})){const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{pid:process.pid}});}`,
    );
    try {
      const socket = await harness.socket();
      const reply = AcpReply(socket);
      harness.initialize(socket);
      const result = (await reply).result as { pid: number };
      const closed = AcpClosed(socket);
      if (kind === "oversized") socket.send("a".repeat(1024 * 1024 + 1));
      else
        socket.send(Buffer.from(kind === "binary" ? [123, 125] : [0xc3, 0x28]), {
          binary: kind === "binary",
        });
      await closed;
      await harness.gateway.close();
      expect(AcpAlive(result.pid)).toBe(false);
    } finally {
      await harness.close();
    }
  },
);

it("forwards an agent JSON object exactly at the 1 MiB limit excluding its NDJSON delimiter", async () => {
  const harness = await AcpHarness(`for await(const line of createInterface({input:process.stdin})){
const x=JSON.parse(line);send({jsonrpc:'2.0',id:x.id,result:{ready:true}});
const message={jsonrpc:'2.0',method:'bounded',params:{text:''}};
message.params.text='a'.repeat(1024*1024-Buffer.byteLength(JSON.stringify(message)));send(message);}`);
  try {
    const socket = await harness.socket();
    const messages: string[] = [];
    socket.on("message", (raw) => messages.push(String(raw)));
    harness.initialize(socket);
    await expect.poll(() => messages.length).toBe(2);
    expect(Buffer.byteLength(messages[1] ?? "")).toBe(1024 * 1024);
    expect(JSON.parse(messages[1] ?? "{}").method).toBe("bounded");
  } finally {
    await harness.close();
  }
});
