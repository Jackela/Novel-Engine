/**
 * Identity contracts: the four wire shapes the auth surface exposes.
 *
 * The password is accepted in a body and never echoed in any response — not in
 * errors, not in session views. That is why there is no "user" object carrying
 * credentials anywhere in these schemas: a shape that cannot hold a password
 * cannot leak one.
 */

import { Type, type Static } from "typebox";

import { EpochMillis } from "./projects.js";

export const OwnerId = Type.String({ minLength: 1, maxLength: 64 });
export type OwnerId = Static<typeof OwnerId>;

/**
 * Setup and login share a shape but not their rules: setup enforces the full
 * password policy, login accepts any string and answers INVALID_OPERATION, so a
 * rejected login does not describe the password policy to an attacker.
 */
export const CredentialsRequest = Type.Object(
  {
    username: Type.String({ maxLength: 200 }),
    /** 72 UTF-8 bytes is bcrypt's window; the length cap here is a transport guard. */
    password: Type.String({ maxLength: 256 }),
  },
  { additionalProperties: false },
);
export type CredentialsRequest = Static<typeof CredentialsRequest>;

/** What setup returns: identity only, no session. */
export const OwnerView = Type.Object(
  {
    ownerId: OwnerId,
    username: Type.String({ maxLength: 200 }),
  },
  { additionalProperties: false },
);
export type OwnerView = Static<typeof OwnerView>;

/** What login returns: identity plus the session's fixed expiry. */
export const SessionView = Type.Object(
  {
    ownerId: OwnerId,
    expiresAt: EpochMillis,
  },
  { additionalProperties: false },
);
export type SessionView = Static<typeof SessionView>;

/**
 * What the probe returns. `authenticated: false` is a 200, not a 401: the entry
 * screen needs to know "no session" to decide what to render, and a 401 would
 * make every first visit look like a failure in the browser console.
 */
export const SessionProbeView = Type.Union([
  Type.Object(
    { authenticated: Type.Literal(true), ownerId: OwnerId, expiresAt: EpochMillis },
    { additionalProperties: false },
  ),
  Type.Object({ authenticated: Type.Literal(false) }, { additionalProperties: false }),
]);
export type SessionProbeView = Static<typeof SessionProbeView>;

export const EmptyResponse = Type.Object({}, { additionalProperties: false });
export type EmptyResponse = Static<typeof EmptyResponse>;
