import { translateActive } from "@/app/i18n/translate";
import { productIdentity } from "@/app/productIdentity";

/**
 * One author-facing boundary for browser transport failures across JSON,
 * downloads, and SSE. The message resolves through the dictionaries at
 * failure time (DR-046), so it follows the active UI language; the product
 * name stays a parameter of the copy.
 */
export function localServiceUnavailable(cause: TypeError): Error {
  return new Error(translateActive("errors.transport.unavailable", { app: productIdentity.name }), {
    cause,
  });
}
