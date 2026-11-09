/**
 * Configure the single local owner.
 *
 * Order matters and is observable:
 * 1. Validate credentials before touching anything — a bad password must not
 *    cost a bcrypt round, and must not depend on whether an owner already exists
 *    (otherwise the error ordering leaks that fact).
 * 2. Refuse if an owner exists. The database enforces the same invariant; this
 *    check exists so the common case fails without hashing.
 * 3. Hash, then write. Hashing is the slow step and must happen outside any
 *    transaction, which is why it sits between two cheap checks.
 *
 * The single-owner rule is a product invariant, not a convenience: every query in
 * the system scopes by owner, and admitting a second owner would silently make
 * each of them see the other's absence rather than an error.
 */

import { type CredentialPolicyError, normalizeOwnerCredentials } from "../domain/credentials.js";
import { OwnerAlreadyConfiguredError } from "../domain/errors.js";
import type { OwnerStore, SecretHasher } from "../ports.js";

export { OwnerAlreadyConfiguredError };

export interface SetupOwnerDeps {
  readonly owners: OwnerStore;
  readonly hasher: SecretHasher;
  /** Epoch millis; injected so tests do not depend on wall time. */
  readonly now: () => number;
}

export interface SetupOwnerInput {
  readonly username: string;
  readonly password: string;
}

export interface SetupOwnerOutput {
  readonly ownerId: string;
  readonly username: string;
}

/**
 * @throws CredentialPolicyError when the username is empty or the password
 * breaks the length rules — the caller maps it to 422 with the specific reason.
 * @throws OwnerAlreadyConfiguredError when an owner already exists — the caller
 * maps it to 422 INVALID_OPERATION, which is what the previous build returned for
 * this case; a 409 here would silently change the wire status.
 */
export async function setupOwner(
  deps: SetupOwnerDeps,
  input: SetupOwnerInput,
): Promise<SetupOwnerOutput> {
  const credentials = normalizeOwnerCredentials(input.username, input.password);
  if (deps.owners.ownerExists()) {
    throw new OwnerAlreadyConfiguredError();
  }
  const passwordHash = await deps.hasher.hash(credentials.password);
  const owner = deps.owners.create(credentials.username, passwordHash, deps.now());
  return { ownerId: owner.id, username: owner.username };
}

/** Re-exported so callers can branch on the violation without a second import. */
export type { CredentialPolicyError };
