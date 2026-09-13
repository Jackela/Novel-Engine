import { makeKeysetCursor } from "../../../../shared/interface/http/canonical_cursor.js";
import type { ExportPageCursor } from "../../application/ports/export_store.js";

const cursor = makeKeysetCursor({
  version: 1,
  scopeCount: 1,
  minNumber: 0,
  numberField: "createdAtMs",
  idMaxLength: 128,
  label: "export",
});

/** Decode the opaque project-bound export catalog position or fail through the validation envelope. */
export function decodeExportCursor(token: string, routeProjectId: string): ExportPageCursor {
  return cursor.decode(token, routeProjectId);
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeExportCursor(
  routeProjectId: string,
  position: ExportPageCursor | null,
): string | null {
  return cursor.encode(routeProjectId, position);
}
