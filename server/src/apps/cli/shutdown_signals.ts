import { closeResourceAndRethrow } from "../api/app_lifecycle.js";

export type ShutdownSignal = "SIGINT" | "SIGTERM";

export type ShutdownSignalHandler = () => void;

/** Minimal event boundary used by the CLI and deterministic lifecycle tests. */
export interface ShutdownSignalSource {
  add(signal: ShutdownSignal, handler: ShutdownSignalHandler): void;
  /** Removing an exact same-source registration is total and must not throw. */
  remove(signal: ShutdownSignal, handler: ShutdownSignalHandler): void;
}

export interface ShutdownSignalLatch {
  /** Resolve once with the first observed signal; this promise never rejects. */
  readonly wait: Promise<ShutdownSignal>;
  /** Remove the exact registered handlers. Safe to call more than once. */
  dispose(): void;
}

export const processShutdownSignalSource: ShutdownSignalSource = {
  add(signal, handler) {
    process.on(signal, handler);
  },
  remove(signal, handler) {
    process.off(signal, handler);
  },
};

export interface CliOwnedServeLifecycle {
  readonly source: ShutdownSignalSource;
  readonly listen: () => Promise<void>;
  readonly close: () => Promise<void>;
}

/** Register both shutdown signals as one first-cause, resolve-only latch. */
export function createShutdownSignalLatch(source: ShutdownSignalSource): ShutdownSignalLatch {
  let resolveSignal: (signal: ShutdownSignal) => void = () => undefined;
  let settled = false;
  let disposed = false;
  const wait = new Promise<ShutdownSignal>((resolve) => {
    resolveSignal = resolve;
  });
  const settle = (signal: ShutdownSignal): void => {
    if (settled) return;
    settled = true;
    resolveSignal(signal);
  };
  const onSigint = (): void => settle("SIGINT");
  const onSigterm = (): void => settle("SIGTERM");

  source.add("SIGINT", onSigint);
  try {
    source.add("SIGTERM", onSigterm);
  } catch (error) {
    source.remove("SIGINT", onSigint);
    throw error;
  }

  return {
    wait,
    dispose() {
      if (disposed) return;
      disposed = true;
      source.remove("SIGINT", onSigint);
      source.remove("SIGTERM", onSigterm);
    },
  };
}

export function signalExitCode(signal: ShutdownSignal): 130 | 143 {
  return signal === "SIGINT" ? 130 : 143;
}

/** Supervise generic listen/close callbacks without owning the Fastify instance. */
export async function runCliOwnedServeLifecycle(
  lifecycle: CliOwnedServeLifecycle,
): Promise<number> {
  let latch: ShutdownSignalLatch;
  try {
    latch = createShutdownSignalLatch(lifecycle.source);
  } catch (error) {
    return closeResourceAndRethrow(
      lifecycle.close,
      error,
      "Signal registration and application cleanup both failed.",
    );
  }

  try {
    await lifecycle.listen();
  } catch (error) {
    try {
      return await closeResourceAndRethrow(
        lifecycle.close,
        error,
        "Server listen and cleanup both failed.",
      );
    } finally {
      latch.dispose();
    }
  }

  const signal = await latch.wait;
  try {
    await lifecycle.close();
  } finally {
    latch.dispose();
  }
  return signalExitCode(signal);
}
