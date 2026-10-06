import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { buildAuthApp, OWNER_PASSWORD, OWNER_USERNAME } from "./auth_helpers.js";

const PUBLIC_HOST = "studio.example.com";
const PROXY_ADDRESS = "10.0.0.7";

/**
 * The browser-facing setup POST as the container sees it behind a TLS
 * proxy: the proxy's address is the socket peer, the public host and the
 * terminated scheme travel in forwarded headers.
 */
function proxiedSetupRequest(app: FastifyInstance, headers: Record<string, string>) {
  return app.inject({
    method: "POST",
    url: "/api/setup",
    remoteAddress: PROXY_ADDRESS,
    headers: {
      host: PUBLIC_HOST,
      "x-forwarded-for": `203.0.113.9, ${PROXY_ADDRESS}`,
      "x-forwarded-proto": "https",
      ...headers,
    },
    payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
  });
}

describe("setup origin behind a trusted TLS proxy", () => {
  it("accepts the public HTTPS origin when the peer is the configured trusted proxy", async () => {
    const { app, directory } = await buildAuthApp({ trustedProxies: [PROXY_ADDRESS] });

    try {
      const token = readFileSync(join(directory, ".setup-token"), "utf8").trim();
      const response = await proxiedSetupRequest(app, {
        origin: `https://${PUBLIC_HOST}`,
        "x-setup-token": token,
      });

      // The expected origin is built from request.protocol, which Fastify
      // resolves from X-Forwarded-Proto only for a trusted peer; the public
      // origin is not in SECURITY_CORS_ORIGINS, so this must be the
      // same-origin path.
      expect(response.statusCode).toBe(201);
    } finally {
      await app.close();
    }
  });

  it("ignores X-Forwarded-Proto from an untrusted peer and refuses the HTTPS origin", async () => {
    const { app } = await buildAuthApp();

    try {
      const response = await proxiedSetupRequest(app, { origin: `https://${PUBLIC_HOST}` });

      expect(response.statusCode).toBe(403);
      expect(response.json().error.code).toBe("FORBIDDEN");
      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(false);
    } finally {
      await app.close();
    }
  });
});
