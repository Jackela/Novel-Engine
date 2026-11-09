/**
 * Errors owned by the identity domain.
 *
 * They live in `domain/` rather than beside the use case because both the use
 * case and the persistence adapter must be able to raise them: the use case
 * refuses a second owner on the cheap path, and the adapter refuses it again
 * when two setups race past that check. If the error lived in the use case, the
 * adapter would have to import from a layer above it.
 */

/**
 * Raised when owner setup runs against an installation that already has one.
 *
 * Maps to **422 INVALID_OPERATION**, matching the previous build: the old store
 * rejected the second owner with `InvalidOperationError`, which the envelope
 * rendered as 422. A 409 would be defensible on REST grounds, but it would
 * change a wire status the contract promises to keep stable. It is also the one
 * identity failure whose message never needs to name a resource — there is only
 * ever one owner.
 */
export class OwnerAlreadyConfiguredError extends Error {
  constructor() {
    super("This installation already has an owner.");
    this.name = "OwnerAlreadyConfiguredError";
  }
}
