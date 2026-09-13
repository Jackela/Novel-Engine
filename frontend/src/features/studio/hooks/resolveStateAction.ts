import type { SetStateAction } from "react";

/**
 * Resolve one React SetStateAction against an already-captured value. Owners
 * that scope stale-owner state synchronously cannot use the updater-function
 * overload, so they reduce the action against the value they captured.
 */
export function resolveStateAction<T>(current: T, action: SetStateAction<T>): T {
  return typeof action === "function" ? (action as (value: T) => T)(current) : action;
}
