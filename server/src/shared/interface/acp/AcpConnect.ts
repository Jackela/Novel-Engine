import type { Readable, Writable } from "node:stream";
import WebSocket from "ws";
import {
  ACP_BUFFER_BYTES,
  ACP_LAUNCH_META,
  ACP_MESSAGE_BYTES,
  type AcpLaunch,
  AcpMessage,
} from "../../application/ports/AcpAgent.js";

export interface AcpConnectOptions {
  readonly url: string;
  readonly token: string;
  readonly launch: AcpLaunch;
  readonly input: Readable;
  readonly output: Writable;
  readonly diagnostic?: (message: string) => void;
  readonly signal?: AbortSignal;
}

/** Connect a stdio client to the gateway without placing credentials in URLs or RPC.
 * Invalid framing, UTF-8, or bounded-buffer overflow terminates the connection with
 * exit code 1; EOF closes it normally, and an abort returns 130. */
export function AcpConnect(options: AcpConnectOptions): Promise<number> {
  const url = new URL(options.url);
  if (
    !["ws:", "wss:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/acp"
  ) {
    throw new Error(
      "ACP gateway URL must be ws(s)://host:port/acp without credentials or query parameters.",
    );
  }
  const socket = new WebSocket(url, {
    headers: { authorization: `Bearer ${options.token}` },
    maxPayload: ACP_MESSAGE_BYTES,
    perMessageDeflate: false,
  });
  return new Promise<number>((resolve) => {
    const decoder = new TextDecoder("utf-8", { fatal: true });
    const wireDecoder = new TextDecoder("utf-8", { fatal: true });
    let buffer = "";
    let initialized = false;
    let queuedBytes = 0;
    let writes = 0;
    let ending = false;
    let exitCode = 0;
    let finished = false;

    const fail = () => {
      if (finished) return;
      exitCode = 1;
      options.diagnostic?.("ACP transport or framing failed.");
      socket.terminate();
    };
    const closeAfterWrites = () => {
      if (ending && writes === 0 && socket.readyState === WebSocket.OPEN) socket.close(1000);
    };
    const send = (line: string) => {
      if (Buffer.byteLength(line) > ACP_MESSAGE_BYTES)
        throw new Error("ACP input frame exceeds its limit.");
      const message = AcpMessage(line);
      if (!initialized) {
        const params = message.params;
        if (
          message.method !== "initialize" ||
          !params ||
          typeof params !== "object" ||
          Array.isArray(params)
        )
          throw new Error("ACP must initialize first.");
        const meta =
          "_meta" in params &&
          params._meta &&
          typeof params._meta === "object" &&
          !Array.isArray(params._meta)
            ? params._meta
            : {};
        message.params = { ...params, _meta: { ...meta, [ACP_LAUNCH_META]: options.launch } };
        initialized = true;
      }
      const text = JSON.stringify(message);
      const bytes = Buffer.byteLength(text);
      if (
        bytes > ACP_MESSAGE_BYTES ||
        queuedBytes + bytes > ACP_BUFFER_BYTES ||
        socket.bufferedAmount + bytes > ACP_BUFFER_BYTES
      )
        throw new Error("ACP outbound buffer exceeds its limit.");
      writes += 1;
      queuedBytes += bytes;
      socket.send(text, (error) => {
        writes -= 1;
        queuedBytes -= bytes;
        if (error) fail();
        else closeAfterWrites();
      });
    };
    const drainLines = () => {
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        send(buffer.slice(0, newline).replace(/\r$/, ""));
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf("\n");
      }
      if (Buffer.byteLength(buffer) > ACP_MESSAGE_BYTES)
        throw new Error("ACP incomplete frame exceeds its limit.");
    };
    const onData = (chunk: Buffer) => {
      try {
        buffer += decoder.decode(chunk, { stream: true });
        drainLines();
      } catch {
        fail();
      }
    };
    const onEnd = () => {
      try {
        buffer += decoder.decode();
        if (buffer) send(buffer);
        ending = true;
        closeAfterWrites();
      } catch {
        fail();
      }
    };
    const onAbort = () => {
      exitCode = 130;
      socket.terminate();
    };
    const onInputClose = () => {
      if (!ending) fail();
    };
    socket.on("open", () => {
      if (options.signal?.aborted) {
        onAbort();
        return;
      }
      options.input.on("data", onData);
      options.input.once("end", onEnd);
      options.input.once("error", fail);
      options.input.once("close", onInputClose);
      if (options.input.readableEnded) {
        onEnd();
        return;
      }
      if (options.input.destroyed) {
        fail();
        return;
      }
      options.input.resume();
    });
    socket.on("message", (data, binary) => {
      if (binary) {
        fail();
        return;
      }
      try {
        const raw = Array.isArray(data)
          ? Buffer.concat(data)
          : Buffer.isBuffer(data)
            ? data
            : Buffer.from(data);
        const text = wireDecoder.decode(raw);
        AcpMessage(text);
        if (options.output.writableLength + Buffer.byteLength(text) + 1 > ACP_BUFFER_BYTES) {
          fail();
          return;
        }
        options.output.write(`${text}\n`, (error) => {
          if (error) fail();
        });
      } catch {
        fail();
      }
    });
    options.output.on("error", fail);
    options.signal?.addEventListener("abort", onAbort, { once: true });
    socket.on("error", fail);
    socket.once("close", (code) => {
      finished = true;
      options.input.pause();
      options.input.off("data", onData);
      options.input.off("end", onEnd);
      options.input.off("error", fail);
      options.input.off("close", onInputClose);
      options.output.off("error", fail);
      options.signal?.removeEventListener("abort", onAbort);
      resolve(exitCode || (ending && code === 1000 ? 0 : 1));
    });
  });
}
