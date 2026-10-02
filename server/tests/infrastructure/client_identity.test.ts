import { describe, expect, it } from "vitest";

import {
  clientIdentity,
  isTrustedProxy,
  isTrustedProxyRange,
} from "../../src/shared/infrastructure/rate_limit/client_identity.js";

describe("trusted proxy matching", () => {
  it("matches exact IPv4 and IPv6 addresses", () => {
    expect(isTrustedProxy("127.0.0.1", ["127.0.0.1"])).toBe(true);
    expect(isTrustedProxy("::1", ["::1"])).toBe(true);
    expect(isTrustedProxy("10.0.0.5", ["127.0.0.1"])).toBe(false);
  });

  it("normalizes IPv4-mapped IPv6 peers to IPv4", () => {
    // Node dual-stack listeners report the loopback peer as ::ffff:127.0.0.1;
    // an exact 127.0.0.1 trust entry must still apply.
    expect(isTrustedProxy("::ffff:127.0.0.1", ["127.0.0.1"])).toBe(true);
    expect(isTrustedProxy("::ffff:10.0.0.5", ["127.0.0.1"])).toBe(false);
  });

  it("never matches a network range: a range can cover clients", () => {
    expect(isTrustedProxy("10.1.2.3", ["10.1.0.0/16"])).toBe(false);
    expect(isTrustedProxy("2001:db8:1::42", ["2001:db8::/32"])).toBe(false);
    expect(isTrustedProxy("10.1.2.3", ["10.0.0.0/8"])).toBe(false);
    expect(isTrustedProxy("10.1.2.3", ["10.1.2.3"])).toBe(true);
  });

  it("falls back to exact host strings for non-IP peers", () => {
    expect(isTrustedProxy("unix:/tmp/sock", ["unix:/tmp/sock"])).toBe(true);
    expect(isTrustedProxy("unknown", ["unix:/tmp/sock"])).toBe(false);
  });
});

describe("network range detection", () => {
  it("flags parseable IP networks across IPv4 and IPv6", () => {
    expect(isTrustedProxyRange("10.0.0.0/8")).toBe(true);
    expect(isTrustedProxyRange("10.1.0.0/16")).toBe(true);
    expect(isTrustedProxyRange("2001:db8::/32")).toBe(true);
    expect(isTrustedProxyRange("0.0.0.0/0")).toBe(true);
  });

  it("keeps concrete addresses and host strings out of the range guard", () => {
    expect(isTrustedProxyRange("127.0.0.1")).toBe(false);
    expect(isTrustedProxyRange("::1")).toBe(false);
    expect(isTrustedProxyRange("unix:/tmp/sock")).toBe(false);
    expect(isTrustedProxyRange("10.0.0.0/999")).toBe(false);
  });
});

describe("client identity resolution", () => {
  it("uses the rightmost forwarded hop behind a trusted proxy", () => {
    expect(clientIdentity("127.0.0.1", "198.51.100.7", ["127.0.0.1"])).toBe("198.51.100.7");
    // Well-formed chains list the client first and every forwarding hop after
    // it; only the rightmost entry is written by the proxy we trust.
    expect(clientIdentity("127.0.0.1", "10.0.0.1", ["127.0.0.1"])).toBe("10.0.0.1");
  });

  it("skips trusted hops and ignores forged leading segments", () => {
    expect(
      clientIdentity("127.0.0.1", "203.0.113.9, 198.51.100.23, 10.0.0.1", [
        "127.0.0.1",
        "10.0.0.1",
      ]),
    ).toBe("198.51.100.23");
    // Rotating the leading (client-controlled) segment cannot move identity.
    expect(clientIdentity("127.0.0.1", "192.0.2.77, 198.51.100.23", ["127.0.0.1"])).toBe(
      "198.51.100.23",
    );
  });

  it("falls back to the peer when every forwarded hop is a trusted proxy", () => {
    expect(clientIdentity("127.0.0.1", "10.0.0.1, 127.0.0.1", ["127.0.0.1", "10.0.0.1"])).toBe(
      "127.0.0.1",
    );
  });

  it("ignores X-Forwarded-For when the peer is untrusted", () => {
    expect(clientIdentity("203.0.113.9", "198.51.100.7", [])).toBe("203.0.113.9");
    expect(clientIdentity("203.0.113.9", "198.51.100.7", ["127.0.0.1"])).toBe("203.0.113.9");
    expect(clientIdentity("203.0.113.9", "198.51.100.7", ["203.0.113.0/24"])).toBe("203.0.113.9");
  });

  it("falls back to the peer address without forwarding data", () => {
    expect(clientIdentity("192.0.2.4", undefined, [])).toBe("192.0.2.4");
    expect(clientIdentity(undefined, undefined, [])).toBe("unknown");
    expect(clientIdentity("127.0.0.1", " , ", ["127.0.0.1"])).toBe("127.0.0.1");
  });
});
