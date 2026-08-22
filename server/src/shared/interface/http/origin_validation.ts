import type { FastifyRequest } from "fastify";

import { LOCALHOST_CORS_PORTS } from "../../domain/cors_contract.js";

const LOCALHOST_PREFIXES = [
  "http://localhost:",
  "https://localhost:",
  "http://127.0.0.1:",
  "https://127.0.0.1:",
];
// scheme://authority[rest] — Origin must never carry path, query, or fragment.
const ORIGIN_PATTERN = /^([a-zA-Z][a-zA-Z0-9+.-]*):\/\/([^/?#]*)([/?#].*)?$/;

interface ParsedBrowserOrigin {
  scheme: string;
  authority: string;
  rest: string | null;
}

/**
 * Parse an Origin/Referer value with the same strictness as the Python gold
 * standard: null when the scheme is not HTTP(S), the authority is missing or
 * carries userinfo, or the port is malformed or out of range.
 */
function parseBrowserOrigin(value: string): ParsedBrowserOrigin | null {
  const match = value.match(ORIGIN_PATTERN);
  if (match === null) {
    return null;
  }
  const scheme = (match[1] ?? "").toLowerCase();
  if (scheme !== "http" && scheme !== "https") {
    return null;
  }
  const authority = (match[2] ?? "").toLowerCase();
  if (authority === "" || authority.includes("@") || authority.includes(" ")) {
    return null;
  }
  const hostPart = authority.startsWith("[")
    ? authority.slice(0, authority.indexOf("]") + 1)
    : authority;
  const portSuffix = authority.slice(hostPart.length);
  if (portSuffix !== "" && !/^:\d{1,5}$/.test(portSuffix)) {
    return null;
  }
  if (portSuffix !== "") {
    const port = Number(portSuffix.slice(1));
    if (port < 1 || port > 65535) {
      return null;
    }
  }
  return { scheme, authority, rest: match[3] ?? null };
}

/** Allow exact configured origins and explicit localhost port wildcards. */
function isConfiguredSetupOrigin(origin: string, corsOrigins: string[]): boolean {
  for (const allowed of corsOrigins) {
    const allowedOrigin = allowed.replace(/\/+$/, "").toLowerCase();
    if (allowedOrigin === "*") {
      continue;
    }
    if (origin === allowedOrigin) {
      return true;
    }
    if (!allowedOrigin.endsWith(":*")) {
      continue;
    }
    const prefix = allowedOrigin.slice(0, -1);
    if (LOCALHOST_PREFIXES.includes(prefix) && origin.startsWith(prefix)) {
      return LOCALHOST_CORS_PORTS.has(origin.slice(prefix.length));
    }
  }
  return false;
}

/**
 * First-run setup has no CSRF cookie yet, so browsers need an origin check
 * instead: Origin and Referer, when present, must match the request's own
 * origin or the configured CORS origins. Requests without browser origin
 * metadata (CLI and bootstrap clients) remain allowed.
 */
export function isSameOriginRequest(request: FastifyRequest, corsOrigins: string[]): boolean {
  const host = String(request.headers.host ?? "").toLowerCase();
  const expected = `${request.protocol.toLowerCase()}://${host}`;
  for (const headerName of ["origin", "referer"] as const) {
    const headerValue = request.headers[headerName];
    if (typeof headerValue !== "string" || headerValue === "") {
      continue;
    }
    if (headerValue.trim().toLowerCase() === "null") {
      return false;
    }
    const parsed = parseBrowserOrigin(headerValue.trim());
    if (parsed === null) {
      return false;
    }
    if (headerName === "origin" && parsed.rest !== null) {
      return false;
    }
    const origin = [parsed.scheme, "://", parsed.authority].join("");
    if (origin !== expected && !isConfiguredSetupOrigin(origin, corsOrigins)) {
      return false;
    }
  }
  return true;
}
