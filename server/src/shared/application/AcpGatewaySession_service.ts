import {
  ACP_BUFFER_BYTES,
  ACP_LAUNCH_META,
  ACP_MESSAGE_BYTES,
  type AcpAgent,
  type AcpAgentLauncher,
  type AcpLaunch,
  AcpMessage,
} from "./ports/AcpAgent.js";

interface AcpPeer {
  readonly send: (message: string) => void;
  readonly fail: () => void;
  readonly diagnostic: (message: string) => void;
}

/** Transparently relay all ACP methods. Protocol and launch failures close the connection
 * and its exclusive process; no method is converted into product authorization. */
export class AcpGatewaySession_service {
  private agent: AcpAgent | undefined;
  private closed = false;
  private pendingBytes = 0;
  private queue = Promise.resolve();

  constructor(
    private readonly launch: AcpAgentLauncher,
    private readonly peer: AcpPeer,
    private readonly token: string,
  ) {}

  accept(text: string): void {
    if (this.closed) return;
    const bytes = Buffer.byteLength(text);
    this.pendingBytes += bytes;
    if (bytes > ACP_MESSAGE_BYTES || this.pendingBytes > ACP_BUFFER_BYTES) {
      this.peer.fail();
      return;
    }
    this.queue = this.queue
      .then(async () => {
        if (this.closed) return;
        const message = AcpMessage(text);
        if (!this.agent) {
          const launch = this.initialize(message);
          const agent = await this.launch(launch, {
            onMessage: (output) => {
              if (this.closed) return;
              try {
                AcpMessage(output);
                this.peer.send(output);
              } catch {
                this.peer.fail();
              }
            },
            onFailure: this.peer.fail,
            diagnostic: this.peer.diagnostic,
            redact: this.token,
          });
          this.agent = agent;
          if (this.closed) {
            await agent.close();
            return;
          }
        }
        this.agent.write(JSON.stringify(message));
      })
      .catch(() => this.peer.fail())
      .finally(() => {
        this.pendingBytes -= bytes;
      });
  }

  private initialize(message: Record<string, unknown>): AcpLaunch {
    if (message.method !== "initialize" || !("id" in message))
      throw new Error("ACP must initialize first.");
    const params = message.params;
    if (!params || typeof params !== "object" || Array.isArray(params))
      throw new Error("ACP initialize requires params.");
    const meta = "_meta" in params ? params._meta : undefined;
    if (!meta || typeof meta !== "object" || Array.isArray(meta))
      throw new Error("ACP initialize requires launch metadata.");
    const launch: unknown = ACP_LAUNCH_META in meta ? meta[ACP_LAUNCH_META] : undefined;
    if (!launch || typeof launch !== "object" || Array.isArray(launch))
      throw new Error("ACP launch descriptor is invalid.");
    const descriptor = launch as Record<string, unknown>;
    if (
      Object.keys(descriptor).some((key) => !["command", "args", "cwd"].includes(key)) ||
      typeof descriptor.command !== "string" ||
      typeof descriptor.cwd !== "string" ||
      !Array.isArray(descriptor.args) ||
      descriptor.args.some((arg) => typeof arg !== "string")
    ) {
      throw new Error("ACP launch descriptor is invalid.");
    }
    const remaining = { ...meta } as Record<string, unknown>;
    delete remaining[ACP_LAUNCH_META];
    message.params = { ...params, _meta: remaining };
    return { command: descriptor.command, args: descriptor.args, cwd: descriptor.cwd };
  }

  async close(): Promise<void> {
    this.closed = true;
    await this.agent?.close();
    await this.queue;
    await this.agent?.close();
  }
}
