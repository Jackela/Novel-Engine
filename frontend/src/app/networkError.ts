import { productIdentity } from "@/app/productIdentity";

/** One author-facing boundary for browser transport failures across JSON, downloads, and SSE. */
export function localServiceUnavailable(cause: TypeError): Error {
  return new Error(`${productIdentity.name} is unavailable. Check the local service and retry.`, {
    cause,
  });
}
