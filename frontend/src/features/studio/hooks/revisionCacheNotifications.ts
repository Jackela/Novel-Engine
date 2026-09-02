import type { RevisionSubscriber } from "./revisionCacheTypes";

export type RevisionErrorFamily = "first" | "older";
export type RevisionRequestOutcome =
  | { readonly kind: "success" }
  | { readonly kind: "error"; readonly reason: unknown };

const subscribers = new Map<string, Map<symbol, RevisionSubscriber>>();
const errorFamilies = new Map<string, RevisionErrorFamily>();

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
    errorFamilies.set(key, family);
    for (const subscriber of snapshot) subscriber.onError(outcome.reason);
    return;
  }
  const trackedFamily = errorFamilies.get(key);
  if (trackedFamily !== undefined && trackedFamily !== family) return;
  errorFamilies.delete(key);
  for (const subscriber of snapshot) subscriber.onSuccess();
}

export function clearRevisionNotifications(key: string): void {
  subscribers.delete(key);
  errorFamilies.delete(key);
}

export function resetRevisionNotifications(): void {
  subscribers.clear();
  errorFamilies.clear();
}
