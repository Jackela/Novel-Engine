import type { OperationCapacityPolicy } from "../../contexts/studio/application/operation_in_flight.js";
import {
  assertWorkflowCapacity,
  type ServerConfig,
} from "../../shared/infrastructure/config/server_config.js";

export interface OperationCapacityAppOptions {
  /** Resolved operational configuration from loadServerConfig. */
  readonly config?: ServerConfig | undefined;
  /** App-owned expensive-workflow limits; direct structured seam for tests. */
  readonly operationCapacity?: OperationCapacityPolicy | undefined;
}

/** Resolve and validate capacity before the composition root creates any runtime resource. */
export function resolveOperationCapacity(
  options: OperationCapacityAppOptions,
): OperationCapacityPolicy | undefined {
  const capacity =
    options.operationCapacity ??
    (options.config === undefined
      ? undefined
      : {
          applicationLimit: options.config.maxActiveWorkflows,
          projectLimit: options.config.maxActiveWorkflowsPerProject,
        });
  if (capacity !== undefined) assertWorkflowCapacity(capacity);
  return capacity;
}
