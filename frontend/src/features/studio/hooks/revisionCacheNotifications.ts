import type { RevisionSubscriber } from "./revisionCacheTypes";

export type RevisionErrorFamily = "first" | "older";
export type RevisionRequestOutcome =
  | { readonly kind: "success" }
  | { readonly kind: "error"; readonly reason: unknown };

const subscribers = new Map<string, Map<symbol, RevisionSubscriber>>();
interface TrackedRevisionError {
  readonly reason: unknown;
  readonly sequence: number;
}
const errorsByOwner = new Map<string, Map<RevisionErrorFamily, TrackedRevisionError>>();
let errorSequence = 0;

export function addRevisionSubscriber(
  key: string,
  token: symbol,
  subscriber: RevisionSubscriber,
): void {
  const ownerSubscribers = subscribers.get(key) ?? new Map<symbol, RevisionSubscriber>();
  ownerSubscribers.set(token, subscriber);
  subscribers.set(key, ownerSubscribers);
}

export function removeRevisionSubscriber(key: string, token: symbol): void {
  const ownerSubscribers = subscribers.get(key);
  ownerSubscribers?.delete(token);
  if (ownerSubscribers?.size === 0) subscribers.delete(key);
}

export function publishRevisionOutcome(
  key: string,
  family: RevisionErrorFamily,
  outcome: RevisionRequestOutcome,
): void {
  const snapshot = [...(subscribers.get(key)?.values() ?? [])];
  if (outcome.kind === "error") {
    const ownerErrors = errorsByOwner.get(key) ?? new Map();
    ownerErrors.set(family, { reason: outcome.reason, sequence: ++errorSequence });
    errorsByOwner.set(key, ownerErrors);
    for (const subscriber of snapshot) subscriber.onError(outcome.reason);
    return;
  }
  const ownerErrors = errorsByOwner.get(key);
  ownerErrors?.delete(family);
  if (!ownerErrors || ownerErrors.size === 0) {
    errorsByOwner.delete(key);
    for (const subscriber of snapshot) subscriber.onSuccess();
    return;
  }
  let latestRemaining: TrackedRevisionError | undefined;
  for (const tracked of ownerErrors.values()) {
    if (!latestRemaining || tracked.sequence > latestRemaining.sequence) latestRemaining = tracked;
  }
  if (!latestRemaining) throw new Error("Expected a remaining revision error.");
  for (const subscriber of snapshot) subscriber.onError(latestRemaining.reason);
}

export function clearRevisionNotifications(key: string): void {
  subscribers.delete(key);
  errorsByOwner.delete(key);
}

export function resetRevisionNotifications(): void {
  subscribers.clear();
  errorsByOwner.clear();
  errorSequence = 0;
}
