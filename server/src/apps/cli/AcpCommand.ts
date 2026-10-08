import type { Readable, Writable } from "node:stream";
import { AcpAgentProcess } from "../../shared/infrastructure/acp/AcpAgentProcess.js";
import { AcpTokenFile } from "../../shared/infrastructure/acp/AcpTokenFile.js";
import { AcpConnect } from "../../shared/interface/acp/AcpConnect.js";
import { AcpGateway } from "../../shared/interface/acp/AcpGateway.js";
import {
  processShutdownSignalSource,
  runCliOwnedServeLifecycle,
  type ShutdownSignalSource,
} from "./shutdown_signals.js";

export interface AcpCommandContext {
  readonly input?: Readable;
  readonly output?: Writable;
  readonly diagnostic?: (message: string) => void;
  readonly shutdownSignalSource?: ShutdownSignalSource;
}

const usage =
  "Usage: novel-engine acp serve --token-file PATH [--host 127.0.0.1] [--port 8710]\n       novel-engine acp connect --url URL --token-file PATH --command COMMAND [--arg ARG ...] --cwd DIR";

/** Compose the standalone ACP runtime without consulting Studio configuration or opening
 * its database. Usage returns 2, operational failure returns 1, and signals close resources. */
export async function AcpCommand(
  argv: readonly string[],
  context: AcpCommandContext = {},
): Promise<number> {
  const diagnostic = context.diagnostic ?? console.error;
  const [operation] = argv;
  const valid =
    operation === "serve"
      ? ["--token-file", "--host", "--port"]
      : operation === "connect"
        ? ["--token-file", "--url", "--command", "--arg", "--cwd"]
        : [];
  const flags = new Map<string, string>();
  const args: string[] = [];
  for (let index = 1; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (
      !flag ||
      value === undefined ||
      !valid.includes(flag) ||
      (flag !== "--arg" && flags.has(flag))
    ) {
      diagnostic(usage);
      return 2;
    }
    if (flag === "--arg") args.push(value);
    else flags.set(flag, value);
  }
  const path = flags.get("--token-file");
  if (!path || !valid.length) {
    diagnostic(usage);
    return 2;
  }
  try {
    if (operation === "serve") {
      const port = Number(flags.get("--port") ?? "8710");
      if (!Number.isInteger(port) || port < 1 || port > 65535) {
        diagnostic("ACP port must be an integer from 1 to 65535.");
        return 2;
      }
      const token = await AcpTokenFile(path, { create: true });
      const gateway = new AcpGateway({ token, launchAgent: AcpAgentProcess.launch, diagnostic });
      return await runCliOwnedServeLifecycle({
        source: context.shutdownSignalSource ?? processShutdownSignalSource,
        listen: async () => {
          const address = await gateway.listen({ host: flags.get("--host") ?? "127.0.0.1", port });
          diagnostic(`ACP gateway listening at ${address.url}`);
        },
        close: () => gateway.close(),
      });
    }
    const url = flags.get("--url");
    const command = flags.get("--command");
    const cwd = flags.get("--cwd");
    if (!url || !command || !cwd) {
      diagnostic(usage);
      return 2;
    }
    const token = await AcpTokenFile(path);
    const controller = new AbortController();
    const source = context.shutdownSignalSource ?? processShutdownSignalSource;
    let signalExit = 0;
    const sigint = () => {
      signalExit = 130;
      controller.abort();
    };
    const sigterm = () => {
      signalExit = 143;
      controller.abort();
    };
    source.add("SIGINT", sigint);
    try {
      source.add("SIGTERM", sigterm);
      try {
        const exit = await AcpConnect({
          url,
          token,
          launch: { command, args, cwd },
          input: context.input ?? process.stdin,
          output: context.output ?? process.stdout,
          diagnostic,
          signal: controller.signal,
        });
        return signalExit || exit;
      } finally {
        source.remove("SIGTERM", sigterm);
      }
    } finally {
      source.remove("SIGINT", sigint);
    }
  } catch (error) {
    diagnostic(error instanceof Error ? error.message : "ACP command failed.");
    return 1;
  }
}
