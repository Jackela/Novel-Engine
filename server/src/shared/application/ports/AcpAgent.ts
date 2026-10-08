/** The launch descriptor is trusted operator input; clients cannot supply an environment. */
export interface AcpLaunch {
  readonly command: string;
  readonly args: readonly string[];
  readonly cwd: string;
}

/** One agent belongs to one connection. Writes refuse bounded-buffer overflow. */
export interface AcpAgent {
  write(message: string): void;
  close(): Promise<void>;
}

export interface AcpAgentEvents {
  readonly onMessage: (message: string) => void;
  readonly onFailure: () => void;
  readonly diagnostic: (message: string) => void;
  readonly redact: string;
}

export type AcpAgentLauncher = (launch: AcpLaunch, events: AcpAgentEvents) => Promise<AcpAgent>;

/** Limits are bytes of encoded transport data, independent of JSON string length. */
export const ACP_MESSAGE_BYTES = 1024 * 1024;
export const ACP_BUFFER_BYTES = 8 * ACP_MESSAGE_BYTES;
export const ACP_LAUNCH_META = "novel-engine/acp-proxy";

/** Refuse invalid JSON-RPC frames before crossing either transport boundary. */
export function AcpMessage(text: string): Record<string, unknown> {
  const value: unknown = JSON.parse(text);
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    !("jsonrpc" in value) ||
    value.jsonrpc !== "2.0"
  ) {
    throw new Error("ACP frame must be a JSON-RPC object.");
  }
  const message = value as Record<string, unknown>;
  if (typeof message.method !== "string" && !("result" in message) && !("error" in message)) {
    throw new Error("ACP frame has no request, notification, or response.");
  }
  return message;
}
