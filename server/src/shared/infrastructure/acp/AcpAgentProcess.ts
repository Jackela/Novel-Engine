import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { realpath, stat } from "node:fs/promises";
import { isAbsolute } from "node:path";
import {
  ACP_BUFFER_BYTES,
  ACP_MESSAGE_BYTES,
  type AcpAgent,
  type AcpAgentEvents,
  type AcpLaunch,
} from "../../application/ports/AcpAgent.js";

/** A detached, directly spawned stdio agent. Malformed UTF-8, oversized lines,
 * stream errors, and process exit notify its connection owner; close kills the group. */
export class AcpAgentProcess implements AcpAgent {
  private output = "";
  private readonly decoder = new TextDecoder("utf-8", { fatal: true });
  private closing: Promise<void> | undefined;

  private constructor(
    private readonly child: ChildProcessWithoutNullStreams,
    private readonly events: AcpAgentEvents,
  ) {
    child.stdout.on("data", (chunk: Buffer) => {
      try {
        this.output += this.decoder.decode(chunk, { stream: true });
        let newline = this.output.indexOf("\n");
        while (newline >= 0) {
          const line = this.output.slice(0, newline).replace(/\r$/, "");
          if (Buffer.byteLength(line) > ACP_MESSAGE_BYTES)
            throw new Error("ACP line exceeds its limit.");
          this.output = this.output.slice(newline + 1);
          events.onMessage(line);
          newline = this.output.indexOf("\n");
        }
        if (Buffer.byteLength(this.output) > ACP_MESSAGE_BYTES)
          throw new Error("ACP incomplete line exceeds its limit.");
      } catch {
        events.onFailure();
      }
    });
    child.stdout.on("end", () => events.onFailure());
    child.stdout.on("error", events.onFailure);
    child.stdin.on("error", events.onFailure);
    child.on("error", events.onFailure);
    child.on("exit", events.onFailure);
    this.stderr();
  }

  static async launch(launch: AcpLaunch, events: AcpAgentEvents): Promise<AcpAgentProcess> {
    if (
      !launch.command ||
      launch.command.includes("\0") ||
      (!isAbsolute(launch.command) && /[/\\]/.test(launch.command)) ||
      launch.args.some((arg) => arg.includes("\0"))
    ) {
      throw new Error("ACP command must be an absolute executable or a PATH name.");
    }
    if (!isAbsolute(launch.cwd)) throw new Error("ACP cwd must be absolute.");
    const cwd = await realpath(launch.cwd);
    if (!(await stat(cwd)).isDirectory()) throw new Error("ACP cwd must be a directory.");
    const env = Object.fromEntries(
      Object.entries(process.env).filter(([, value]) => !value?.includes(events.redact)),
    );
    const child = spawn(launch.command, [...launch.args], {
      cwd,
      env,
      shell: false,
      detached: process.platform !== "win32",
      stdio: ["pipe", "pipe", "pipe"],
    });
    const agent = new AcpAgentProcess(child, events);
    await new Promise<void>((resolve, reject) => {
      child.once("spawn", resolve);
      child.once("error", reject);
    });
    return agent;
  }

  write(message: string): void {
    if (
      this.closing ||
      this.child.stdin.writableLength + Buffer.byteLength(message) + 1 > ACP_BUFFER_BYTES
    )
      throw new Error("ACP agent input buffer exceeded its limit.");
    this.child.stdin.write(`${message}\n`);
  }

  private stderr(): void {
    let pending = "";
    let budget = 16 * 1024;
    const secrets = [
      this.events.redact,
      ...Object.entries(process.env)
        .filter(
          ([name, value]) => /key|secret|token|password/i.test(name) && value && value.length >= 6,
        )
        .map(([, value]) => value ?? ""),
    ];
    const report = (line: string) => {
      if (budget <= 0) return;
      let safe = Array.from(line, (character) => {
        const code = character.charCodeAt(0);
        return code < 32 || code === 127 ? " " : character;
      }).join("");
      for (const secret of secrets) if (secret) safe = safe.split(secret).join("[redacted]");
      safe = safe.slice(0, budget);
      budget -= safe.length;
      this.events.diagnostic(safe);
    };
    this.child.stderr.on("data", (chunk: Buffer) => {
      if (budget <= 0) return;
      pending += chunk.toString("utf8");
      let newline = pending.indexOf("\n");
      while (newline >= 0) {
        if (newline > 16 * 1024) {
          report("ACP agent diagnostic line exceeded its limit.");
          pending = "";
          budget = 0;
          return;
        }
        report(pending.slice(0, newline));
        pending = pending.slice(newline + 1);
        newline = pending.indexOf("\n");
      }
      if (pending.length > 16 * 1024) {
        pending = "";
        report("ACP agent diagnostic line exceeded its limit.");
        budget = 0;
      }
    });
    this.child.stderr.on("end", () => {
      if (pending) report(pending);
    });
    this.child.stderr.on("error", this.events.onFailure);
  }

  close(): Promise<void> {
    this.closing ??= this.killTree();
    return this.closing;
  }

  private async killTree(): Promise<void> {
    this.child.stdin.destroy();
    const pid = this.child.pid;
    if (!pid) return;
    if (process.platform === "win32") {
      const killer = spawn("taskkill.exe", ["/pid", String(pid), "/T", "/F"], {
        stdio: "ignore",
        shell: false,
      });
      await new Promise<void>((resolve, reject) => {
        killer.once("error", reject);
        killer.once("exit", () => resolve());
      });
      return;
    }
    const kill = async (signal: NodeJS.Signals) => {
      try {
        process.kill(-pid, signal);
      } catch (error) {
        if (error instanceof Error && "code" in error && error.code === "ESRCH") return;
        // macOS can report EPERM between stdio closure and waitpid reaping an
        // exited group leader. Retry once after that finite reaping window;
        // a persistent permission failure remains visible to the lifecycle owner.
        if (error instanceof Error && "code" in error && error.code === "EPERM") {
          await new Promise<void>((resolve) => setTimeout(resolve, 25));
          try {
            process.kill(-pid, signal);
            return;
          } catch (retry) {
            if (retry instanceof Error && "code" in retry && retry.code === "ESRCH") return;
            throw new Error(`ACP process group ${pid} ${signal} cleanup failed.`, { cause: retry });
          }
        }
        throw new Error(`ACP process group ${pid} ${signal} cleanup failed.`, { cause: error });
      }
    };
    await kill("SIGTERM");
    await new Promise<void>((resolve) => setTimeout(resolve, 150));
    await kill("SIGKILL");
  }
}
