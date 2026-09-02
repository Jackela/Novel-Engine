import type {
  ShutdownSignal,
  ShutdownSignalHandler,
  ShutdownSignalSource,
} from "../../../src/apps/cli/shutdown_signals.js";

export class FakeShutdownSignalSource implements ShutdownSignalSource {
  readonly events: string[] = [];
  readonly added: Array<{ signal: ShutdownSignal; handler: ShutdownSignalHandler }> = [];
  readonly removed: Array<{ signal: ShutdownSignal; handler: ShutdownSignalHandler }> = [];
  readonly listeners = new Map<ShutdownSignal, Set<ShutdownSignalHandler>>();

  constructor(private readonly failRegistrationWith?: Error) {}

  add(signal: ShutdownSignal, handler: ShutdownSignalHandler): void {
    this.events.push(`add:${signal}`);
    if (signal === "SIGTERM" && this.failRegistrationWith !== undefined) {
      throw this.failRegistrationWith;
    }
    this.added.push({ signal, handler });
    const handlers = this.listeners.get(signal) ?? new Set<ShutdownSignalHandler>();
    handlers.add(handler);
    this.listeners.set(signal, handlers);
  }

  remove(signal: ShutdownSignal, handler: ShutdownSignalHandler): void {
    this.events.push(`remove:${signal}`);
    this.removed.push({ signal, handler });
    this.listeners.get(signal)?.delete(handler);
  }

  emit(signal: ShutdownSignal): void {
    this.events.push(`emit:${signal}`);
    for (const handler of this.listeners.get(signal) ?? []) handler();
  }

  listenerCount(signal: ShutdownSignal): number {
    return this.listeners.get(signal)?.size ?? 0;
  }
}
