/**
 * Domain policy violations of the studio: the requested operation is invalid
 * for the current state (weak setup credentials, duplicate owner, failed
 * login, ...). The HTTP layer maps these to 422 under the unified envelope.
 */
export class InvalidOperationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidOperationError";
  }
}
