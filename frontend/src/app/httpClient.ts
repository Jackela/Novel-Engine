import { appConfig } from "@/app/config";
import { localServiceUnavailable } from "@/app/networkError";
import { createRequestAbortScope } from "@/app/requestAbortScope";

export class HttpError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
    readonly code?: string,
  ) {
    super(message);
    Object.setPrototypeOf(this, HttpError.prototype);
  }
}

const url = (path: string) => (appConfig.apiBaseUrl ? `${appConfig.apiBaseUrl}${path}` : path);

/** Absolute-API-aware URL builder shared by the streaming client (#308). */
export const apiUrl = url;

export function getCsrfToken(): string | undefined {
  if (typeof document === "undefined") {
    return undefined;
  }
  const engine = document.cookie.match(/(?:^|; )novel_engine_csrf=([^;]*)/);
  return engine?.[1];
}

type ResponseParser<T> = (value: unknown) => T;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Read an error response in the unified envelope shape
 * `{ error: { code, message, details } }`. Unknown bodies fall back to the
 * caller's status message.
 */
export async function readHttpError(
  response: Response,
  fallbackMessage: string,
): Promise<HttpError> {
  const payload = await response.json().catch(() => null);
  if (isRecord(payload) && isRecord(payload.error)) {
    const envelope = payload.error;
    const message = typeof envelope.message === "string" ? envelope.message : fallbackMessage;
    const code = typeof envelope.code === "string" ? envelope.code : undefined;
    return new HttpError(message, response.status, envelope.details, code);
  }
  return new HttpError(fallbackMessage, response.status, undefined, undefined);
}

export async function request<T>(
  path: string,
  init: RequestInit | undefined,
  parse: ResponseParser<T>,
): Promise<T> {
  const abortScope = createRequestAbortScope(init?.signal);
  try {
    let response: Response;
    try {
      const method = init?.method?.toUpperCase();
      const csrfToken =
        method && ["POST", "PUT", "PATCH", "DELETE"].includes(method) ? getCsrfToken() : undefined;
      response = await fetch(url(path), {
        credentials: "include",
        ...init,
        headers: {
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
          ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
          ...(init?.headers ?? {}),
        },
        signal: abortScope.signal,
      });
    } catch (error) {
      if (
        (error instanceof Error || error instanceof DOMException) &&
        error.name === "AbortError"
      ) {
        throw new Error(
          abortScope.timedOut() ? "Request timed out. Please retry." : "Request cancelled.",
          { cause: error },
        );
      }
      if (error instanceof TypeError) {
        throw localServiceUnavailable(error);
      }
      throw error;
    }
    if (!response.ok) {
      throw await readHttpError(response, `Request failed with status ${response.status}`);
    }
    if (response.status === 204) return parse(undefined);
    return parse(await response.json());
  } finally {
    abortScope.dispose();
  }
}

export const json = (value: unknown) => JSON.stringify(value);

export const postJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: "POST", body: json(value) }, parse);
export const putJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: "PUT", body: json(value) }, parse);
export const patchJson = <T>(
  path: string,
  value: unknown,
  parse: ResponseParser<T>,
  init?: RequestInit,
) => request(path, { ...init, method: "PATCH", body: json(value) }, parse);

export async function downloadBlob(path: string, init?: RequestInit): Promise<Blob> {
  const abortScope = createRequestAbortScope(init?.signal);
  try {
    const response = await fetch(url(path), {
      credentials: "include",
      ...init,
      signal: abortScope.signal,
    });
    if (!response.ok) {
      throw await readHttpError(response, `Download failed with status ${response.status}`);
    }
    return await response.blob();
  } catch (error) {
    if (error instanceof HttpError) throw error;
    if ((error instanceof Error || error instanceof DOMException) && error.name === "AbortError") {
      throw new Error(
        abortScope.timedOut() ? "Download timed out. Please retry." : "Request cancelled.",
        { cause: error },
      );
    }
    if (error instanceof TypeError) {
      throw localServiceUnavailable(error);
    }
    throw error;
  } finally {
    abortScope.dispose();
  }
}
