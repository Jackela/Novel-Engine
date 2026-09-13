import type { FastifyInstance } from "fastify";

import type { InjectedResponse } from "./auth_helpers.js";
import { type CookieJar, call } from "./studio_helpers.js";

/** Send a retry request with the caller-owned durable attempt identity. */
export function retryJobRequest(
  app: FastifyInstance,
  jar: CookieJar,
  url: string,
  idempotencyKey: string,
): Promise<InjectedResponse> {
  return call(app, jar, "POST", url, undefined, { "idempotency-key": idempotencyKey });
}
