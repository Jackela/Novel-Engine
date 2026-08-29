/**
 * Public entry for provider-scaffold detection. The implementation is split
 * into a character/JSON-candidate reader and a pattern scanner; this module
 * keeps the external API stable.
 */
export { hasProviderScaffolding } from "./provider_scaffold_scanner.js";
