import { ConfigurationError } from "./configuration_error.js";

/**
 * Workflow-capacity configuration surface (#461), split out of
 * `server_config.ts` for the file-size budget: the bounded integer range is
 * one policy shared by the environment loader and the composition-root seam,
 * so both must refuse the same values with the same message.
 */
export const MIN_ACTIVE_WORKFLOWS = 1;
export const MAX_ACTIVE_WORKFLOWS = 1024;
export const DEFAULT_MAX_ACTIVE_WORKFLOWS = 4;
export const DEFAULT_MAX_ACTIVE_WORKFLOWS_PER_PROJECT = 2;

export interface WorkflowCapacityConfig {
  readonly applicationLimit: number;
  readonly projectLimit: number;
}

/** Validate the structured composition-root seam before persistence opens. */
export function assertWorkflowCapacity(capacity: WorkflowCapacityConfig): void {
  assertCapacityValue("application", capacity.applicationLimit);
  assertCapacityValue("project", capacity.projectLimit);
  if (capacity.projectLimit > capacity.applicationLimit) {
    throw new ConfigurationError(
      "Workflow capacity project limit must not exceed the application limit",
    );
  }
}

function assertCapacityValue(name: string, value: number): void {
  if (!Number.isInteger(value) || value < MIN_ACTIVE_WORKFLOWS || value > MAX_ACTIVE_WORKFLOWS) {
    throw new ConfigurationError(
      `Workflow capacity ${name} limit must be an integer between ${MIN_ACTIVE_WORKFLOWS} and ${MAX_ACTIVE_WORKFLOWS}`,
    );
  }
}
