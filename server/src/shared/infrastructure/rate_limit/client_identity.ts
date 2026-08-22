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

function groupsToValue(rawGroups: string[]): bigint | null {
  const groups: string[] = [];
  for (let index = 0; index < rawGroups.length; index += 1) {
    const group = rawGroups[index];
    if (group === undefined) {
      return null;
    }
    if (group.includes(".")) {
      // An embedded IPv4 tail (e.g. ::ffff:127.0.0.1) expands to two groups.
      if (index !== rawGroups.length - 1) {
        return null;
      }
      const embedded = parseIPv4(group);
      if (embedded === null) {
        return null;
      }
      groups.push(((embedded >> 16n) & 0xffffn).toString(16), (embedded & 0xffffn).toString(16));
      continue;
    }
    groups.push(group);
  }
  if (groups.length !== 8) {
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
    const missing = 8 - leftGroups.length - rightGroups.length;
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
export function parseIpAddress(text: string): ParsedAddress | null {
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
 * Whether the peer matches a configured trusted proxy: an exact IP, a CIDR
 * network, or an exact host string (for local sockets and test clients).
 */
export function isTrustedProxy(host: string, trustedProxies: string[]): boolean {
  const address = parseIpAddress(host);
  for (const proxy of trustedProxies) {
    const slash = proxy.indexOf("/");
    if (slash === -1) {
      const proxyAddress = parseIpAddress(proxy);
      if (
        address !== null &&
        proxyAddress !== null &&
        proxyAddress.bits === address.bits &&
        proxyAddress.value === address.value
      ) {
        return true;
      }
      if (address === null && host === proxy) {
        return true;
      }
      continue;
    }
    const network = parseIpAddress(proxy.slice(0, slash));
    const prefix = Number(proxy.slice(slash + 1));
    if (network === null || !Number.isInteger(prefix) || prefix < 0 || prefix > network.bits) {
      continue;
    }
    if (address !== null && address.bits === network.bits) {
      const shift = BigInt(network.bits - prefix);
      if (address.value >> shift === network.value >> shift) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Rate-limit client identity: the first X-Forwarded-For entry only when the
 * immediate peer is a trusted proxy; otherwise the peer address itself, so an
 * untrusted client cannot shuffle identities with forged headers.
 */
export function clientIdentity(
  remoteAddress: string | undefined,
  forwardedFor: string | undefined,
  trustedProxies: string[],
): string {
  const peer = remoteAddress ?? "unknown";
  if (forwardedFor !== undefined && isTrustedProxy(peer, trustedProxies)) {
    const first = forwardedFor.split(",")[0]?.trim();
    if (first !== undefined && first !== "") {
      return first;
    }
  }
  return peer;
}
