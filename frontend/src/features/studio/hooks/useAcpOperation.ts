import { useCallback, useEffect, useRef, useState } from "react";
import { ACP_REQUEST_TIMEOUT_MS, type AiExecutionOptions } from "@/app/AiExecutionOptions";
import { api, HttpError } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import { observeAiOperation } from "@/app/observeAiOperation";
import type { AiOperationEvent, ExternalEffects } from "@/app/parseAiOperationEvent";
import { toErrorMessage } from "./toErrorMessage";

export type AcpExecute = <T>(
  provider: string,
  operation: (options?: AiExecutionOptions) => Promise<T>,
  signal?: AbortSignal,
) => Promise<T>;
export interface AcpOperationView {
  readonly id: string;
  readonly phase: "connecting" | "running" | "waiting" | "completed" | "cancelled" | "error";
  readonly tools: readonly Extract<AiOperationEvent, { type: "tool" }>[];
  readonly permissions: readonly Extract<AiOperationEvent, { type: "permission" }>[];
  readonly effects: ExternalEffects;
  readonly error: string | null;
  readonly decidingPermissionIds: readonly string[];
}
interface ActiveOperation {
  readonly controller: AbortController;
  readonly decisions: Set<string>;
  submitted: boolean;
}

/** Own concurrent ACP observations for one project; navigation cancels all of them. */
export function useAcpOperation(projectId: string, onSessionLost?: () => void) {
  const [operations, setOperations] = useState<readonly AcpOperationView[]>([]);
  const active = useRef(new Map<string, ActiveOperation>());
  const ownerProject = useRef(projectId);
  const live = useRef(true);
  const sessionLost = useRef(onSessionLost);
  useEffect(() => {
    sessionLost.current = onSessionLost;
  }, [onSessionLost]);
  useEffect(() => {
    ownerProject.current = projectId;
    live.current = true;
    return () => {
      live.current = false;
      for (const operation of active.current.values()) operation.controller.abort();
      active.current.clear();
    };
  }, [projectId]);
  const update = useCallback((id: string, apply: (view: AcpOperationView) => AcpOperationView) => {
    if (live.current)
      setOperations((current) => current.map((view) => (view.id === id ? apply(view) : view)));
  }, []);

  const execute: AcpExecute = useCallback(
    async (provider, operation, externalSignal) => {
      if (provider !== "acp") return operation();
      if (!live.current || ownerProject.current !== projectId)
        throw new Error(translateActive("acp.error.missingObserver"));
      const id = crypto.randomUUID();
      const controller = new AbortController();
      const record: ActiveOperation = { controller, decisions: new Set(), submitted: false };
      active.current.set(id, record);
      setOperations((current) => [
        ...current.filter((view) => active.current.has(view.id)),
        ...current
          .filter((view) => !active.current.has(view.id) && view.effects !== "none")
          .slice(-2),
        {
          id,
          phase: "connecting",
          tools: [],
          permissions: [],
          effects: "none",
          error: null,
          decidingPermissionIds: [],
        },
      ]);
      const abortFromExternal = () => controller.abort();
      externalSignal?.addEventListener("abort", abortFromExternal, { once: true });
      if (externalSignal?.aborted) controller.abort();
      let rejectCancelled: (reason: unknown) => void = () => undefined;
      const cancelled = new Promise<never>((_, reject) => {
        rejectCancelled = reject;
      });
      const cancel = () => {
        rejectCancelled(new DOMException("Operation cancelled", "AbortError"));
        update(id, (view) => ({
          ...view,
          phase: view.phase === "completed" || view.phase === "error" ? view.phase : "cancelled",
          permissions: [],
          effects:
            view.effects === "completed"
              ? "completed"
              : record.submitted || view.tools.length > 0
                ? "unknown"
                : view.effects,
        }));
      };
      controller.signal.addEventListener("abort", cancel, { once: true });
      if (controller.signal.aborted) cancel();
      const deadline = window.setTimeout(() => controller.abort(), ACP_REQUEST_TIMEOUT_MS);
      const observation = observeAiOperation({
        projectId,
        operationId: id,
        signal: controller.signal,
        onEvent: (event) => {
          if (!active.current.has(id) || controller.signal.aborted) return;
          update(id, (view) => {
            switch (event.type) {
              case "ready":
                return { ...view, phase: "running" };
              case "tool":
                return {
                  ...view,
                  tools: [...view.tools.filter((tool) => tool.tool_id !== event.tool_id), event],
                  effects:
                    event.status === "completed" &&
                    ["edit", "delete", "move", "execute", "other"].includes(event.kind)
                      ? "completed"
                      : view.effects,
                };
              case "permission":
                return {
                  ...view,
                  phase: "waiting",
                  permissions: [
                    ...view.permissions.filter(
                      (permission) => permission.permission_id !== event.permission_id,
                    ),
                    event,
                  ],
                };
              case "completed":
                return {
                  ...view,
                  phase: "completed",
                  permissions: [],
                  effects: event.external_effects,
                };
              case "error":
                return {
                  ...view,
                  phase: "error",
                  permissions: [],
                  error: event.message,
                  effects: event.external_effects,
                };
            }
          });
        },
      });
      const observationFailure = observation.done.catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          update(id, (view) => ({
            ...view,
            phase: "error",
            error: toErrorMessage(reason, translateActive("acp.error.observationLost")),
            effects:
              view.effects === "completed" ? "completed" : record.submitted ? "unknown" : "none",
          }));
          if (reason instanceof HttpError && reason.status === 401) sessionLost.current?.();
          controller.abort();
        }
        throw reason;
      });
      // The handler is attached before awaiting ready so an early transport error is owned.
      void observationFailure.catch(() => undefined);
      try {
        await Promise.race([observation.ready, cancelled]);
        record.submitted = true;
        const result = operation({
          signal: controller.signal,
          headers: { "X-AI-Operation-Id": id },
          timeoutMs: ACP_REQUEST_TIMEOUT_MS,
        });
        return await Promise.race([
          Promise.all([result, observationFailure]).then(([value]) => value),
          cancelled,
        ]);
      } catch (reason) {
        if (!controller.signal.aborted) {
          update(id, (view) => ({
            ...view,
            phase: "error",
            permissions: [],
            error: toErrorMessage(reason, translateActive("acp.error.observationLost")),
            effects:
              view.effects === "completed" ? "completed" : record.submitted ? "unknown" : "none",
          }));
          if (reason instanceof HttpError && reason.status === 401) sessionLost.current?.();
        }
        throw reason;
      } finally {
        active.current.delete(id);
        controller.signal.removeEventListener("abort", cancel);
        controller.abort();
        externalSignal?.removeEventListener("abort", abortFromExternal);
        window.clearTimeout(deadline);
      }
    },
    [projectId, update],
  );

  const respond = useCallback(
    async (id: string, permissionId: string, optionId: string) => {
      const operation = active.current.get(id);
      if (
        !operation ||
        operation.controller.signal.aborted ||
        operation.decisions.has(permissionId)
      )
        return;
      operation.decisions.add(permissionId);
      update(id, (view) => ({
        ...view,
        decidingPermissionIds: [...view.decidingPermissionIds, permissionId],
        error: null,
      }));
      try {
        await api.respondAiPermission(projectId, id, permissionId, optionId, {
          signal: operation.controller.signal,
        });
        if (active.current.get(id) === operation && !operation.controller.signal.aborted)
          update(id, (view) => {
            const permissions = view.permissions.filter(
              (permission) => permission.permission_id !== permissionId,
            );
            return {
              ...view,
              permissions,
              phase: permissions.length > 0 ? "waiting" : "running",
              decidingPermissionIds: view.decidingPermissionIds.filter((id) => id !== permissionId),
            };
          });
      } catch (reason) {
        if (!operation.controller.signal.aborted) {
          update(id, (view) => ({
            ...view,
            decidingPermissionIds: view.decidingPermissionIds.filter((id) => id !== permissionId),
            error: toErrorMessage(reason, translateActive("acp.error.permission")),
          }));
          if (reason instanceof HttpError && reason.status === 401) {
            sessionLost.current?.();
            operation.controller.abort();
          }
        }
      } finally {
        operation.decisions.delete(permissionId);
      }
    },
    [projectId, update],
  );
  const cancel = useCallback((id: string) => {
    active.current.get(id)?.controller.abort();
  }, []);
  return { operations, execute, respond, cancel };
}
