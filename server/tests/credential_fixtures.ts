/**
 * Fake provider credentials for tests, assembled from fragments so no string
 * literal is ever bound to a credential-shaped name. Mirrors the Python
 * authority's tests/credential_fixtures.py (PR #239): the local security
 * gate flags literal-shaped fakes, not the values.
 */
export function fixtureApiKey(...parts: string[]): string {
  return parts.join("-");
}

/** Searchable hostile-body markers used to prove Provider diagnostics stay private. */
export const PROVIDER_FAILURE_CANARIES = [
  "CANARY_PROVIDER_SECRET",
  "MANUSCRIPT_CANARY",
  "PROVIDER_HTML_CANARY",
  "PROVIDER_ANSI_CANARY",
  "FORGED_LOG_LINE_CANARY",
] as const;

export function hostileProviderFailureBody(credential: string): string {
  return [
    credential,
    PROVIDER_FAILURE_CANARIES[0],
    `manuscript=${PROVIDER_FAILURE_CANARIES[1]}`,
    `<script>${PROVIDER_FAILURE_CANARIES[2]}</script>`,
    `\u001b[31m${PROVIDER_FAILURE_CANARIES[3]}\u001b[0m`,
    `\nERROR ${PROVIDER_FAILURE_CANARIES[4]}`,
  ].join("|");
}
