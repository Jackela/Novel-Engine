/**
 * The schema barrel. Import tables from here, never from a domain file
 * directly, so a future split of one domain does not ripple through the
 * adapters.
 *
 * Load order matters for the generated SQL: `identity` before `library` before
 * `manuscript` before `generation` before `delivery`, because each domain
 * references tables declared before it.
 */

export * from "./identity.js";
export * from "./library.js";
export * from "./manuscript.js";
export * from "./generation.js";
export * from "./delivery.js";
export * from "./system.js";
