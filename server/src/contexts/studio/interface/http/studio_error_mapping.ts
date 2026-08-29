import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import {
  AppError,
  INVALID_OPERATION_CODE,
  INVALID_OPERATION_STATUS_CODE,
} from "../../../../shared/interface/http/error_envelope.js";
import {
  DuplicateDocumentError,
  DuplicateVolumeError,
  NotFoundError,
  OperationInFlightError,
  RevisionConflictError,
  SnapshotConflict,
} from "../../domain/exceptions.js";

/**
 * Translate studio domain failures into the unified error envelope. Unknown
 * failures rethrow untouched: programming errors must stay visible and reach
 * the opaque 500 handler.
 */
function toAppError(error: unknown): unknown {
  if (error instanceof NotFoundError) {
    return new AppError({ statusCode: 404, code: "NOT_FOUND", message: error.message });
  }
  if (error instanceof DuplicateVolumeError) {
    return new AppError({ statusCode: 409, code: "VOLUME_CONFLICT", message: error.message });
  }
  if (error instanceof RevisionConflictError) {
    return new AppError({
      statusCode: 409,
      code: "REVISION_CONFLICT",
      message: error.message,
      details: { current_revision_id: error.currentRevisionId },
    });
  }
  if (error instanceof SnapshotConflict) {
    return new AppError({ statusCode: 409, code: "SNAPSHOT_CONFLICT", message: error.message });
  }
  if (error instanceof DuplicateDocumentError) {
    return new AppError({ statusCode: 409, code: "DOCUMENT_CONFLICT", message: error.message });
  }
  if (error instanceof OperationInFlightError) {
    return new AppError({
      statusCode: 409,
      code: "OPERATION_IN_FLIGHT",
      message: error.message,
      details: {
        project_id: error.projectId,
        document_id: error.documentId,
        operation: error.operation,
      },
    });
  }
  if (error instanceof InvalidOperationError) {
    return new AppError({
      statusCode: INVALID_OPERATION_STATUS_CODE,
      code: INVALID_OPERATION_CODE,
      message: error.message,
    });
  }
  return error;
}

/** Run a studio operation with domain-to-envelope error translation. */
export function withStudioErrors<T>(operation: () => T): T {
  try {
    return operation();
  } catch (error) {
    throw toAppError(error);
  }
}

/**
 * `withStudioErrors` is synchronous; async studio operations (generation,
 * review, retry, artifact delivery) must map rejections through the same
 * single translation channel.
 */
export async function withAsyncStudioErrors<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    throw toAppError(error);
  }
}
