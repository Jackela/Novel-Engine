import type { Principal } from "../../../../shared/application/ports/auth.js";

/**
 * Owner scoping of every project query: the single principal since #311
 * retired the guest.
 */
export interface ProjectScope {
  ownerId: string;
}

/** Derive the store scope from the authenticated owner principal. */
export function scopeForPrincipal(principal: Principal): ProjectScope {
  if (principal.ownerId === null) {
    throw new Error("A principal without an owner cannot scope studio data.");
  }
  return { ownerId: principal.ownerId };
}
