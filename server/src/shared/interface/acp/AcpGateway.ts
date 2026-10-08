import { timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { WebSocket, WebSocketServer } from "ws";
import { AcpGatewaySession_service } from "../../application/AcpGatewaySession_service.js";
import {
  ACP_BUFFER_BYTES,
  ACP_MESSAGE_BYTES,
  type AcpAgentLauncher,
} from "../../application/ports/AcpAgent.js";

export interface AcpGatewayOptions {
  readonly token: string;
  readonly launchAgent: AcpAgentLauncher;
  readonly diagnostic?: (message: string) => void;
}

/** Build an isolated authenticated ACP gateway. Only trusted non-browser clients may
 * upgrade at /acp; close drains every connection's process cleanup before returning. */
export class AcpGateway {
  private readonly server = createServer((_request, response) => {
    response.writeHead(404);
    response.end();
  });
  private readonly sockets = new WebSocketServer({
    noServer: true,
    maxPayload: ACP_MESSAGE_BYTES,
    perMessageDeflate: false,
  });
  private readonly sessions = new Set<AcpGatewaySession_service>();
  private readonly cleanups = new Set<Promise<void>>();
  private readonly cleanupErrors: unknown[] = [];
  private closing: Promise<void> | undefined;

  constructor(private readonly options: AcpGatewayOptions) {
    this.server.on("upgrade", (request, socket, head) => {
      const header = request.headers.authorization;
      const expected = Buffer.from(`Bearer ${options.token}`);
      const actual = Buffer.from(header ?? "");
      if (
        request.url !== "/acp" ||
        request.headers.origin !== undefined ||
        actual.length !== expected.length ||
        !timingSafeEqual(actual, expected)
      ) {
        socket.end("HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n");
        return;
      }
      this.sockets.handleUpgrade(request, socket, head, (peer) => this.connection(peer));
    });
  }

  async listen(
    input: { readonly host?: string; readonly port?: number } = {},
  ): Promise<{ url: string; port: number }> {
    const host = input.host ?? "127.0.0.1";
    await new Promise<void>((resolve, reject) => {
      this.server.once("error", reject);
      this.server.listen(input.port ?? 8710, host, () => {
        this.server.off("error", reject);
        resolve();
      });
    });
    const { port } = this.server.address() as AddressInfo;
    return { url: `ws://${host.includes(":") ? `[${host}]` : host}:${port}/acp`, port };
  }

  private connection(peer: WebSocket): void {
    const diagnostic = this.options.diagnostic ?? (() => undefined);
    const fail = () => {
      peer.close(1011, "ACP connection failed");
      peer.terminate();
    };
    const session = new AcpGatewaySession_service(
      this.options.launchAgent,
      {
        send: (message) => {
          if (
            peer.readyState !== WebSocket.OPEN ||
            peer.bufferedAmount + Buffer.byteLength(message) > ACP_BUFFER_BYTES
          ) {
            fail();
            return;
          }
          peer.send(message, (error) => {
            if (error) fail();
          });
        },
        fail,
        diagnostic,
      },
      this.options.token,
    );
    this.sessions.add(session);
    const decoder = new TextDecoder("utf-8", { fatal: true });
    peer.on("message", (data, binary) => {
      if (binary) {
        fail();
        return;
      }
      try {
        session.accept(decoder.decode(data as Buffer));
      } catch {
        fail();
      }
    });
    peer.on("error", fail);
    peer.once("close", () => {
      const cleanup = session.close().catch((error: unknown) => {
        this.cleanupErrors.push(error);
        diagnostic("ACP agent process cleanup failed.");
      });
      this.cleanups.add(cleanup);
      void cleanup.finally(() => {
        this.sessions.delete(session);
        this.cleanups.delete(cleanup);
      });
    });
  }

  close(): Promise<void> {
    this.closing ??= this.shutdown();
    return this.closing;
  }

  private async shutdown(): Promise<void> {
    for (const peer of this.sockets.clients) peer.terminate();
    await Promise.all([...this.sessions].map((session) => session.close()));
    await Promise.all(this.cleanups);
    await new Promise<void>((resolve, reject) =>
      this.sockets.close((error) => (error ? reject(error) : resolve())),
    );
    if (this.server.listening)
      await new Promise<void>((resolve, reject) =>
        this.server.close((error) => (error ? reject(error) : resolve())),
      );
    if (this.cleanupErrors.length)
      throw new AggregateError(this.cleanupErrors, "ACP process cleanup failed.");
  }
}
