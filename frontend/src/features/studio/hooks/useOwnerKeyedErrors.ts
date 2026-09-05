import type { Dispatch, SetStateAction } from "react";
import { useCallback, useMemo, useState } from "react";

type ErrorPublishers<Source extends string> = Record<
  Source,
  Dispatch<SetStateAction<string | null>>
>;

export function combineErrorMessages(...messages: readonly (string | null)[]): string | null {
  const visible = messages.filter((message): message is string => Boolean(message));
  return visible.length > 0 ? visible.join(" ") : null;
}

function resolveError(
  current: string | null,
  action: SetStateAction<string | null>,
): string | null {
  return typeof action === "function" ? action(current) : action;
}

/**
 * Retains independent error slots for each owner and source. Switching owners
 * changes only the visible projection; it neither leaks nor discards errors.
 */
export function useOwnerKeyedErrors<const Source extends string>(
  ownerKey: string,
  sources: readonly Source[],
): {
  readonly error: string | null;
  readonly errors: Readonly<Record<Source, string | null>>;
  readonly publishers: ErrorPublishers<Source>;
} {
  const [errorsByOwner, setErrorsByOwner] = useState<
    ReadonlyMap<string, ReadonlyMap<Source, string>>
  >(() => new Map());

  const publish = useCallback(
    (source: Source, action: SetStateAction<string | null>) => {
      setErrorsByOwner((current) => {
        const currentSources = current.get(ownerKey) ?? new Map<Source, string>();
        const nextError = resolveError(currentSources.get(source) ?? null, action);
        const nextSources = new Map(currentSources);
        if (nextError === null) nextSources.delete(source);
        else nextSources.set(source, nextError);
        const next = new Map(current);
        if (nextSources.size === 0) next.delete(ownerKey);
        else next.set(ownerKey, nextSources);
        return next;
      });
    },
    [ownerKey],
  );

  const publishers = useMemo(
    () =>
      Object.fromEntries(
        sources.map((source) => [
          source,
          (action: SetStateAction<string | null>) => publish(source, action),
        ]),
      ) as ErrorPublishers<Source>,
    [publish, sources],
  );
  const messages = sources.flatMap((source) => {
    const message = errorsByOwner.get(ownerKey)?.get(source);
    return message ? [message] : [];
  });
  const errors = Object.fromEntries(
    sources.map((source) => [source, errorsByOwner.get(ownerKey)?.get(source) ?? null]),
  ) as Record<Source, string | null>;

  return { error: combineErrorMessages(...messages), errors, publishers };
}
