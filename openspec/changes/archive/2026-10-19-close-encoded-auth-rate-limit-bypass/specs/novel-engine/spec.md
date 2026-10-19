## MODIFIED Requirements

### Requirement: Authentication endpoint rate limiting
The setup and login endpoints MUST be rate limited per client IP with a
token bucket defaulting to five requests per minute. Excess requests MUST
receive 429 with a `Retry-After` header in seconds under the unified error
envelope, and MUST NOT trigger authentication side effects. Client identity
MUST use the rightmost `X-Forwarded-For` hop that is not itself a trusted
proxy, and only when the immediate peer is a configured trusted proxy;
otherwise it MUST be the peer address itself. Trusted proxy entries MUST be
exact IP addresses or hosts — network ranges are refused at configuration
load, because a range that covers clients would let a client pose as a proxy
and rotate forged chains into fresh buckets. Preflight `OPTIONS` requests are
exempt.

All URL spellings that the router resolves to the same authentication endpoint
MUST share that client IP and HTTP method's rate-limit bucket. Encoded path
characters and query strings MUST NOT bypass admission or create a fresh
bucket. Exhausted admission MUST still return the structured 429 before body
validation or persistence availability can trigger another response.

#### Scenario: Burst exhausted
- **GIVEN** the default five-per-minute limit
- **WHEN** a sixth setup or login request arrives from the same client IP within the window
- **THEN** the status is 429 with a `Retry-After` of at least one second
- **AND** no session or owner state changes

#### Scenario: Untrusted proxy cannot shuffle identity
- **GIVEN** no trusted proxies are configured
- **WHEN** requests from one peer address present differing `X-Forwarded-For` values
- **THEN** they share a single bucket keyed by the peer address

#### Scenario: Forged leading segments cannot mint identities
- **GIVEN** a trusted proxy is configured and requests arrive through it from one client
- **WHEN** the client varies the leading `X-Forwarded-For` segments on every request
- **THEN** every request shares the bucket of the rightmost untrusted hop
- **AND** the sixth request is rejected with 429

#### Scenario: Network ranges are refused as trusted proxies
- **GIVEN** `SECURITY_TRUSTED_PROXIES` contains a network range
- **WHEN** the configuration loads
- **THEN** it fails with a configuration error instead of trusting the range

#### Scenario: Encoded setup paths cannot bypass an exhausted bucket
- **GIVEN** one client has exhausted the default setup limit through canonical and encoded spellings of the setup route
- **WHEN** it submits valid setup credentials and any required setup token through another spelling of that same route
- **THEN** the response is the structured 429 with a Retry-After header
- **AND** no Owner is created

#### Scenario: Encoded login paths cannot mint a fresh bucket
- **GIVEN** one client has exhausted the default login limit through failed requests to equivalent spellings of the login route
- **WHEN** it submits correct credentials through an encoded spelling or a query-bearing spelling of that route
- **THEN** the response is the same structured 429 and no session cookies are issued

#### Scenario: Admission remains early on equivalent setup routes
- **GIVEN** the database-free application has exhausted one client's GET setup bucket
- **WHEN** that client requests an equivalent encoded setup URL
- **THEN** it receives 429 rather than persistence-unavailable or validation work
- **AND** another client or HTTP method retains its independent bucket
