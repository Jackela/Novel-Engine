import { appConfig } from "./config";

/** Combine caller cancellation with the API timeout and expose its winning cause. */
export function createRequestAbortScope(externalSignal: AbortSignal | null | undefined) {
  const controller = new AbortController();
  let timedOut = false;
  const abortFromExternal = () => controller.abort(externalSignal?.reason);
  externalSignal?.addEventListener("abort", abortFromExternal, { once: true });
  if (externalSignal?.aborted) abortFromExternal();
  const timeout = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, appConfig.apiTimeoutMs);
  return {
    signal: controller.signal,
    timedOut: () => timedOut,
    dispose: () => {
      window.clearTimeout(timeout);
      externalSignal?.removeEventListener("abort", abortFromExternal);
    },
  };
}
