import { existsSync, realpathSync, statSync } from "node:fs";
import { extname, isAbsolute, relative, resolve, sep } from "node:path";
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
 * Compare paths structurally instead of with a string prefix. The candidate
 * must remain below the root both before and after resolving symlinks.
 */
function isInsideDirectory(root: string, candidate: string): boolean {
  const pathFromRoot = relative(root, candidate);
  return (
    pathFromRoot === "" ||
    (!isAbsolute(pathFromRoot) && pathFromRoot !== ".." && !pathFromRoot.startsWith(`..${sep}`))
  );
}

function resolveDistDirectory(distDirectory: string): string | null {
  if (!existsSync(distDirectory)) {
    return null;
  }
  const resolvedDirectory = realpathSync(distDirectory);
  return statSync(resolvedDirectory).isDirectory() ? resolvedDirectory : null;
}

/**
 * Resolve a requested static file to a canonical relative path. Resolving the
 * candidate through realpath prevents an in-dist symlink from escaping the
 * built SPA directory before @fastify/static opens the file.
 */
function resolveStaticFile(distRoot: string, rawPath: string): string | null {
  if (rawPath.includes("\0")) {
    return null;
  }
  const candidate = resolve(distRoot, rawPath);
  if (!isInsideDirectory(distRoot, candidate) || !existsSync(candidate)) {
    return null;
  }
  const resolvedCandidate = realpathSync(candidate);
  if (!isInsideDirectory(distRoot, resolvedCandidate) || !statSync(resolvedCandidate).isFile()) {
    return null;
  }
  return relative(distRoot, resolvedCandidate);
}

/**
 * Client routes are segment paths. A static namespace or a file extension is
 * an asset identity, so a missing request there must reach the normal 404.
 */
function hasAssetIdentity(rawPath: string): boolean {
  return rawPath === "assets" || rawPath.startsWith("assets/") || extname(rawPath) !== "";
}

function isReservedPath(rawPath: string): boolean {
  return rawPath === "api" || RESERVED_PATH_PREFIXES.some((prefix) => rawPath.startsWith(prefix));
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
  const distRoot = resolveDistDirectory(distDirectory);

  if (distRoot !== null) {
    // Route-less registration: only reply.sendFile is decorated, so every
    // serving decision stays explicit in the catch-all below.
    await app.register(fastifyStatic, {
      root: distRoot,
      serve: false,
      decorateReply: true,
    });
  }

  app.get<{ Params: { "*": string } }>("/*", { schema: { hide: true } }, async (request, reply) => {
    const rawPath = String(request.params["*"] ?? "");
    if (isReservedPath(rawPath)) {
      // Reserved prefixes keep the pre-SPA behavior: the unified envelope.
      return reply.callNotFound();
    }
    if (distRoot === null) {
      return reply.send({
        name: options.productName,
        version: options.version,
        message: UNBUILT_DIST_MESSAGE,
      });
    }
    const staticFile = resolveStaticFile(distRoot, rawPath);
    if (staticFile !== null) {
      // Content-hashed bundles under assets/ are immutable; everything the
      // shell references by stable name (index.html, favicon, ...) must
      // revalidate so new deploys are picked up.
      return sendSpaFile(reply, staticFile, { immutable: staticFile.startsWith("assets/") });
    }
    if (hasAssetIdentity(rawPath)) {
      return reply.callNotFound();
    }
    return sendSpaFile(reply, "index.html", { immutable: false });
  });
}
