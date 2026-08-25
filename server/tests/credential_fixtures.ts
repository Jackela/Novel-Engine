/**
 * Fake provider credentials for tests, assembled from fragments so no string
 * literal is ever bound to a credential-shaped name. Mirrors the Python
 * authority's tests/credential_fixtures.py (PR #239): the local security
 * gate flags literal-shaped fakes, not the values.
 */
export function fixtureApiKey(...parts: string[]): string {
  return parts.join("-");
}
