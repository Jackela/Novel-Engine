import type { EventEmitter } from "node:events";

interface ArtifactDownloadResponse extends EventEmitter {
  readonly writableFinished: boolean;
  readonly destroyed?: boolean | undefined;
  readonly closed?: boolean | undefined;
}

interface ArtifactDownloadRequest extends EventEmitter {
  readonly aborted?: boolean | undefined;
  readonly destroyed?: boolean | undefined;
}

interface ArtifactDownloadSocket extends EventEmitter {
  readonly destroyed?: boolean | undefined;
  readonly closed?: boolean | undefined;
}

export interface ArtifactDownloadResponseLifetimeOptions {
  readonly response: ArtifactDownloadResponse;
  readonly request?: ArtifactDownloadRequest | undefined;
  readonly socket?: ArtifactDownloadSocket | undefined;
  readonly send: () => void;
}

/** Keeps the caller's download reservation until the response finishes or disconnects. */
export function sendWithinArtifactResponseLifetime(
  options: ArtifactDownloadResponseLifetimeOptions,
): Promise<void> {
  const { response, request, socket } = options;
  return new Promise((resolve, reject) => {
    let settled = false;
    const cleanup = (): void => {
      response.off("finish", finish);
      response.off("close", close);
      response.off("error", fail);
      request?.off("aborted", close);
      socket?.off("close", close);
    };
    const settle = (failure?: unknown): void => {
      if (settled) return;
      settled = true;
      cleanup();
      if (failure === undefined) resolve();
      else reject(failure);
    };
    const finish = (): void => settle();
    const close = (): void => settle();
    const fail = (error: unknown): void => settle(error);

    response.once("finish", finish);
    response.once("close", close);
    response.once("error", fail);
    request?.once("aborted", close);
    socket?.once("close", close);
    if (isClosed(response, request, socket)) {
      settle();
      return;
    }
    try {
      options.send();
      if (isClosed(response, request, socket)) settle();
    } catch (error) {
      settle(error);
    }
  });
}

function isClosed(
  response: ArtifactDownloadResponse,
  request: ArtifactDownloadRequest | undefined,
  socket: ArtifactDownloadSocket | undefined,
): boolean {
  return (
    response.writableFinished ||
    response.destroyed === true ||
    response.closed === true ||
    request?.aborted === true ||
    request?.destroyed === true ||
    socket?.destroyed === true ||
    socket?.closed === true
  );
}
