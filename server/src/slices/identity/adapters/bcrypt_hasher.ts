/**
 * bcrypt hashing, behind the `SecretHasher` port.
 *
 * Cost 12 is the adjudicated tradeoff: about 200 ms per hash on the target
 * hardware. Slow enough that guessing is expensive, fast enough that a login
 * feels immediate. It is also why the use cases check cheap preconditions
 * (password length, owner existence) **before** calling `hash` — an avoidable
 * 200 ms per request is a self-inflicted bottleneck.
 *
 * The dummy hash exists for one purpose: to spend the same 200 ms when no owner
 * matched, so response latency cannot answer "does this username exist". Its
 * salt is random per process, so no usable password literal ever lives in source
 * control. It is memoized because regenerating it per request would make the
 * unknown-user path *slower* than the known-user path — leaking the answer in the
 * opposite direction.
 */

import { randomBytes } from "node:crypto";

import { compare, hash } from "bcryptjs";

import type { SecretHasher } from "../ports.js";

export const DEFAULT_BCRYPT_ROUNDS = 12;

export function createBcryptHasher(rounds: number = DEFAULT_BCRYPT_ROUNDS): SecretHasher {
  let dummy: Promise<string> | undefined;
  return {
    hash: (plain) => hash(plain, rounds),
    verify: (plain, stored) => compare(plain, stored),
    dummy: () => {
      dummy ??= hash(randomBytes(32).toString("base64url"), rounds);
      return dummy;
    },
  };
}
