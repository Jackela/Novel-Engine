import { ApiContractError } from "./apiContract";
import { apiUrl, readHttpError } from "./httpClient";
import { translateActive } from "./i18n/translate";
import { localServiceUnavailable } from "./networkError";
import { type AiOperationEvent, parseAiOperationEvent } from "./parseAiOperationEvent";

interface ObservationOptions {
  readonly projectId: string;
  readonly operationId: string;
  readonly signal: AbortSignal;
  readonly onEvent: (event: AiOperationEvent) => void;
}

/** Open the authenticated observation before starting an ACP operation. */
export function observeAiOperation({
  projectId,
  operationId,
  signal,
  onEvent,
}: ObservationOptions) {
  let resolveReady: () => void = () => undefined;
  let rejectReady: (reason: unknown) => void = () => undefined;
  const ready = new Promise<void>((resolve, reject) => {
    resolveReady = resolve;
    rejectReady = reject;
  });
  const done = (async () => {
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    let terminal = false;
    let isReady = false;
    const cancel = () => {
      void reader?.cancel().catch(() => undefined);
    };
    signal.addEventListener("abort", cancel, { once: true });
    try {
      const response = await fetch(
        apiUrl(
          `/api/projects/${encodeURIComponent(projectId)}/ai-operations/${encodeURIComponent(operationId)}/events`,
        ),
        { credentials: "include", headers: { Accept: "text/event-stream" }, signal },
      );
      if (!response.ok)
        throw await readHttpError(
          response,
          translateActive("errors.transport.requestFailed", { status: response.status }),
        );
      if (!response.body) throw new ApiContractError("AI operation: no event stream");
      reader = response.body.getReader();
      if (signal.aborted) cancel();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!signal.aborted) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true }).replace(/\r\n/g, "\n");
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const data = frame
            .split("\n")
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).trimStart())
            .join("\n");
          if (data) {
            const event = parseAiOperationEvent(JSON.parse(data));
            if (event.type === "ready") {
              if (event.operation_id !== operationId)
                throw new ApiContractError("AI operation: mismatched operation ID");
              isReady = true;
              resolveReady();
            } else if (!isReady) throw new ApiContractError("AI operation: missing ready");
            if (signal.aborted) return;
            onEvent(event);
            terminal = event.type === "completed" || event.type === "error";
            if (terminal) return;
          }
          boundary = buffer.indexOf("\n\n");
        }
      }
      if (!terminal) throw new Error(translateActive("acp.error.observationLost"));
    } catch (reason) {
      const error = reason instanceof TypeError ? localServiceUnavailable(reason) : reason;
      rejectReady(error);
      throw error;
    } finally {
      if (!isReady) rejectReady(new Error(translateActive("acp.error.observationLost")));
      signal.removeEventListener("abort", cancel);
      await reader?.cancel().catch(() => undefined);
      reader?.releaseLock();
    }
  })();
  return { ready, done };
}
