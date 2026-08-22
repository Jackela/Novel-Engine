import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import { AppError } from "../../../../shared/interface/http/error_envelope.js";
import {
  DuplicateDocumentError,
  NotFoundError,
  RevisionConflictError,
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
  if (error instanceof RevisionConflictError) {
    return new AppError({
      statusCode: 409,
      code: "REVISION_CONFLICT",
      message: error.message,
      details: { current_revision_id: error.currentRevisionId },
    });
  }
  if (error instanceof DuplicateDocumentError) {
    return new AppError({ statusCode: 409, code: "DOCUMENT_CONFLICT", message: error.message });
  }
  if (error instanceof InvalidOperationError) {
    return new AppError({ statusCode: 422, code: "INVALID_OPERATION", message: error.message });
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
