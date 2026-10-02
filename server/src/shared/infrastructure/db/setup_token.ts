import { randomBytes, timingSafeEqual } from "node:crypto";
import { chmodSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { errorCode } from "../error_code.js";

/** Data-directory file holding the one-time first-start setup token. */
export const SETUP_TOKEN_FILENAME = ".setup-token";

/** Random token material: 32 bytes rendered as 43 base64url characters. */
const TOKEN_BYTES = 32;

/**
 * The first-boot gate the auth routes apply to every non-loopback
 * `POST /api/setup`. The token is one-time: it is valid only while no owner
 * is configured and is dropped after a successful setup.
 */
export interface FirstBootSetupToken {
  /** Constant-time check of the presented `x-setup-token` value. */
  verify(provided: string | undefined): boolean;
  /** Drop the token and delete its file; called after a successful setup. */
  invalidate(): void;
}

interface ArmFirstBootSetupTokenOptions {
  /** Data directory of the content-authority database. */
  readonly directory: string;
  readonly ownerExists: boolean;
  /** Receives the active token while no owner is configured (log it once here). */
  readonly onToken: (token: string) => void;
  /** Receives non-fatal file failures; the gate itself always fails closed. */
  readonly onWarning: (message: string, error: unknown) => void;
}

function constantTimeTokenEquals(provided: string, expected: string): boolean {
  const providedBytes = Buffer.from(provided, "utf8");
  const expectedBytes = Buffer.from(expected, "utf8");
  if (providedBytes.length !== expectedBytes.length) {
    return false;
  }
  return timingSafeEqual(providedBytes, expectedBytes);
}

function removeStaleTokenFile(
  tokenPath: string,
  onWarning: (message: string, error: unknown) => void,
): void {
  try {
    unlinkSync(tokenPath);
  } catch (error) {
    if (errorCode(error) !== "ENOENT") {
      onWarning("stale setup token file could not be removed while an owner exists", error);
    }
  }
}

function readOrCreateToken(
  tokenPath: string,
  onWarning: (message: string, error: unknown) => void,
): string | null {
  try {
    const existing = readFileSync(tokenPath, "utf8").trim();
    if (existing !== "") {
      return existing;
    }
  } catch (error) {
    if (errorCode(error) !== "ENOENT") {
      onWarning("setup token file could not be read; non-loopback setup stays locked", error);
      return null;
    }
  }
  const token = randomBytes(TOKEN_BYTES).toString("base64url");
  try {
    writeFileSync(tokenPath, `${token}\n`, { mode: 0o600 });
    chmodSync(tokenPath, 0o600);
    return token;
  } catch (error) {
    onWarning("setup token file could not be written; non-loopback setup stays locked", error);
    return null;
  }
}

/**
 * Arm the first-boot setup token for one data directory. While no owner is
 * configured the endpoint `POST /api/setup` requires this token from every
 * non-loopback peer: the token is generated on first boot, written to
 * `.setup-token` with mode 0600, and reported through `onToken` so the
 * composition root can print it once in the server log. An existing token
 * file is reused so a restart before setup does not invalidate the printed
 * value; a token file left behind once an owner exists is removed. Every
 * failure path fails closed — a missing, unreadable, or unwritable token
 * file leaves non-loopback setup rejected — while loopback setup stays
 * available for the author running the server on the host.
 */
export function armFirstBootSetupToken(
  options: ArmFirstBootSetupTokenOptions,
): FirstBootSetupToken {
  const tokenPath = join(options.directory, SETUP_TOKEN_FILENAME);
  if (options.ownerExists) {
    removeStaleTokenFile(tokenPath, options.onWarning);
    return {
      verify: () => false,
      invalidate: () => {},
    };
  }
  let activeToken = readOrCreateToken(tokenPath, options.onWarning);
  if (activeToken !== null) {
    options.onToken(activeToken);
  }
  return {
    verify: (provided) =>
      provided !== undefined &&
      activeToken !== null &&
      constantTimeTokenEquals(provided, activeToken),
    invalidate: () => {
      activeToken = null;
      try {
        unlinkSync(tokenPath);
      } catch (error) {
        if (errorCode(error) !== "ENOENT") {
          options.onWarning("setup token file could not be removed after owner setup", error);
        }
      }
    },
  };
}
