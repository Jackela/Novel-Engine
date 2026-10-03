import { isIP } from "node:net";

/**
 * Loopback detection for internal-only surfaces (the first-boot setup
 * exemption and the DR-041 `/metrics` gate), evaluated on the raw socket peer
 * address — never on `request.ip`, which trusted-proxy handling can rewrite
 * from client-controlled forwarding headers. `undefined` (no peer, e.g. a
 * Unix socket) fails closed as non-loopback.
 */
export function isLoopbackPeerAddress(address: string | undefined): boolean {
  if (address === undefined) {
    return false;
  }
  const normalized = address.startsWith("::ffff:") ? address.slice("::ffff:".length) : address;
  return normalized === "::1" || (isIP(normalized) === 4 && normalized.startsWith("127."));
}
