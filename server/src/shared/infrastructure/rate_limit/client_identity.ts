interface ParsedAddress {
  value: bigint;
  bits: 32 | 128;
}

function parseIPv4(text: string): bigint | null {
  const parts = text.split(".");
  if (parts.length !== 4) {
    return null;
  }
  let value = 0n;
  for (const part of parts) {
    if (!/^\d{1,3}$/.test(part)) {
      return null;
    }
    const octet = Number(part);
    if (octet > 255) {
      return null;
    }
    value = (value << 8n) | BigInt(octet);
  }
  return value;
}

/** An embedded IPv4 tail counts as two 16-bit groups. */
function unitCount(groups: string[]): number {
  let units = 0;
  for (const group of groups) {
    units += group.includes(".") ? 2 : 1;
  }
  return units;
}

function groupsToValue(rawGroups: string[]): bigint | null {
  const groups: string[] = [];
  let units = 0;
  for (let index = 0; index < rawGroups.length; index += 1) {
    const group = rawGroups[index];
    if (group === undefined) {
      return null;
    }
    if (group.includes(".")) {
      // An embedded IPv4 tail (e.g. ::ffff:127.0.0.1) expands to two groups
      // and must sit at the end.
      if (index !== rawGroups.length - 1) {
        return null;
      }
      const embedded = parseIPv4(group);
      if (embedded === null) {
        return null;
      }
      groups.push(((embedded >> 16n) & 0xffffn).toString(16), (embedded & 0xffffn).toString(16));
      units += 2;
      continue;
    }
    groups.push(group);
    units += 1;
  }
  if (units !== 8) {
    return null;
  }
  let value = 0n;
  for (const group of groups) {
    if (!/^[0-9a-fA-F]{1,4}$/.test(group)) {
      return null;
    }
    value = (value << 16n) | BigInt(Number.parseInt(group, 16));
  }
  return value;
}

function parseIPv6(text: string): bigint | null {
  const zoneIndex = text.indexOf("%");
  const head = zoneIndex === -1 ? text : text.slice(0, zoneIndex);
  const doubleColon = head.indexOf("::");
  if (doubleColon !== -1) {
    if (head.indexOf("::", doubleColon + 1) !== -1) {
      return null;
    }
    const left = head.slice(0, doubleColon);
    const right = head.slice(doubleColon + 2);
    const leftGroups = left === "" ? [] : left.split(":");
    const rightGroups = right === "" ? [] : right.split(":");
    const missing = 8 - unitCount(leftGroups) - unitCount(rightGroups);
    if (missing < 1) {
      return null;
    }
    return groupsToValue([
      ...leftGroups,
      ...Array.from({ length: missing }, () => "0"),
      ...rightGroups,
    ]);
  }
  return groupsToValue(head.split(":"));
}

/** Parse an IPv4 or IPv6 literal; IPv4-mapped IPv6 compares as its IPv4 value. */
function parseIpAddress(text: string): ParsedAddress | null {
  const v4 = parseIPv4(text);
  if (v4 !== null) {
    return { value: v4, bits: 32 };
  }
  const v6 = parseIPv6(text);
  if (v6 === null) {
    return null;
  }
  if (v6 >> 32n === 0xffffn) {
    return { value: v6 & ((1n << 32n) - 1n), bits: 32 };
  }
  return { value: v6, bits: 128 };
}

/**
 * Whether a configured trust entry is a network range rather than one concrete
 * address. Configuration refuses such entries: a range that happens to cover
 * clients would let a client connecting directly pose as a trusted proxy and
 * rotate forged forwarding chains into fresh rate-limit buckets.
 */
export function isTrustedProxyRange(entry: string): boolean {
  const slash = entry.indexOf("/");
  if (slash === -1) {
    return false;
  }
  const network = parseIpAddress(entry.slice(0, slash));
  if (network === null) {
    return false;
  }
  const prefix = Number(entry.slice(slash + 1));
  return Number.isInteger(prefix) && prefix >= 0 && prefix <= network.bits;
}

/**
 * Whether the peer matches a configured trusted proxy: an exact IP address or
 * an exact host string (for local sockets and test clients). Network ranges
 * never match — not even as host strings — so no configuration shape can grant
 * a client the forwarding trust the rate limiter relies on.
 */
export function isTrustedProxy(host: string, trustedProxies: string[]): boolean {
  const address = parseIpAddress(host);
  for (const proxy of trustedProxies) {
    if (isTrustedProxyRange(proxy)) {
      continue;
    }
    const proxyAddress = parseIpAddress(proxy);
    if (address !== null && proxyAddress !== null) {
      if (proxyAddress.bits === address.bits && proxyAddress.value === address.value) {
        return true;
      }
      continue;
    }
    if (address === null && host === proxy) {
      return true;
    }
  }
  return false;
}

/**
 * Rate-limit client identity: the rightmost forwarded hop that is not itself a
 * trusted proxy, and only when the immediate peer is a trusted proxy;
 * otherwise the peer address itself. The trusted proxy writes the rightmost
 * entry from the connection it accepted, so a client can rotate the leading
 * (self-described) segments without minting a new identity. When every hop is
 * a trusted proxy, the peer is returned: those requests share one bucket,
 * which can throttle but never bypasses the limit.
 */
export function clientIdentity(
  remoteAddress: string | undefined,
  forwardedFor: string | undefined,
  trustedProxies: string[],
): string {
  const peer = remoteAddress ?? "unknown";
  if (forwardedFor === undefined || !isTrustedProxy(peer, trustedProxies)) {
    return peer;
  }
  const hops = forwardedFor.split(",").map((hop) => hop.trim());
  for (let index = hops.length - 1; index >= 0; index -= 1) {
    const hop = hops[index];
    if (hop !== undefined && hop !== "" && !isTrustedProxy(hop, trustedProxies)) {
      return hop;
    }
  }
  return peer;
}
