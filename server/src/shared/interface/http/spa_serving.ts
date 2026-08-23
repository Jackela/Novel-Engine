import { existsSync, statSync } from "node:fs";
import { isAbsolute, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

import fastifyStatic from "@fastify/static";
import type { FastifyInstance, FastifyReply } from "fastify";

/**
 * SPA serving for the Studio shell (#274): the TS backend serves the built
 * frontend at the site root so deep links land in the client router. Static
 * bytes always flow through @fastify/static (content typing, ranges, ETag,
 * root containment); this module only decides routing — exact dist file,
 * index.html fallback, or the unbuilt-dist notice.
 */

export interface SpaServingOptions {
  /** Directory holding the built SPA contents (frontend/dist). */
  readonly distDirectory: string;
  readonly productName: string;
  readonly version: string;
}

/** Python-parity prefixes that must never resolve to SPA HTML. */
const RESERVED_PATH_PREFIXES = ["api/", "health", "metrics", "docs", "openapi"] as const;

const UNBUILT_DIST_MESSAGE = "Build frontend/ to enable the Studio UI.";

/** Hashed bundles under assets/ never change content, so they cache forever. */
const IMMUTABLE_MAX_AGE_MS = 365 * 24 * 60 * 60 * 1000;

/**
 * Default dist location: `<workspace root>/frontend/dist`, resolved relative
 * to this module (server/src/shared/interface/http → five levels up to the
 * pnpm workspace root). Deployments override through AppOptions at the
 * composition root.
 */
export function defaultSpaDistDirectory(): string {
  return fileURLToPath(new URL("../../../../../frontend/dist", import.meta.url));
}

/**
 * Normalize a wildcard path and reject escapes: only paths that stay inside
 * the dist root after normalization are file candidates. This mirrors the
 * Python resolve-and-contain check; the actual byte stream still comes from
 * @fastify/static's root-contained send.
 */
function containedRelative(rawPath: string): string | null {
  if (rawPath.includes("\0")) {
    return null;
  }
  const normalized = normalize(rawPath);
  if (isAbsolute(normalized) || normalized === ".." || normalized.startsWith("../")) {
    return null;
  }
  return normalized;
}

function isReservedPath(rawPath: string): boolean {
  return rawPath === "api" || RESERVED_PATH_PREFIXES.some((prefix) => rawPath.startsWith(prefix));
}

function isFileCandidate(distDirectory: string, relativePath: string): boolean {
  const candidate = join(distDirectory, relativePath);
  return existsSync(candidate) && statSync(candidate).isFile();
}

function sendSpaFile(
  reply: FastifyReply,
  relativePath: string,
  options: { immutable: boolean },
): FastifyReply {
  if (options.immutable) {
    return reply.sendFile(relativePath, {
      cacheControl: true,
      maxAge: IMMUTABLE_MAX_AGE_MS,
      immutable: true,
    });
  }
  return reply.sendFile(relativePath, { cacheControl: true, maxAge: 0 });
}

/**
 * Mount the SPA surface: the catch-all serves exact dist files, falls back
 * to index.html for client routes, keeps reserved API/ops prefixes on the
 * unified 404 envelope, and — when no build exists — boots API-only with a
 * notice payload instead of HTML.
 */
export async function registerSpaServing(
  app: FastifyInstance,
  options: SpaServingOptions,
): Promise<void> {
  const { distDirectory } = options;
  const distPresent = existsSync(distDirectory) && statSync(distDirectory).isDirectory();

  if (distPresent) {
    // Route-less registration: only reply.sendFile is decorated, so every
    // serving decision stays explicit in the catch-all below.
    await app.register(fastifyStatic, {
      root: distDirectory,
      serve: false,
      decorateReply: true,
    });
  }

  app.get(
    "/*",
    { schema: { hide: true } },
    async (request, reply) => {
      const rawPath = String(request.params["*"] ?? "");
      if (isReservedPath(rawPath)) {
        // Reserved prefixes keep the pre-SPA behavior: the unified envelope.
        return reply.callNotFound();
      }
      if (!distPresent) {
        return reply.send({
          name: options.productName,
          version: options.version,
          message: UNBUILT_DIST_MESSAGE,
        });
      }
      const relative = containedRelative(rawPath);
      if (relative !== null && isFileCandidate(distDirectory, relative)) {
        // Content-hashed bundles under assets/ are immutable; everything the
        // shell references by stable name (index.html, favicon, ...) must
        // revalidate so new deploys are picked up.
        return sendSpaFile(reply, relative, { immutable: relative.startsWith("assets/") });
      }
      return sendSpaFile(reply, "index.html", { immutable: false });
    },
  );
}
