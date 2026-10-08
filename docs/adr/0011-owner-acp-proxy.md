# ADR-0011: Owner-operated ACP proxy and request-scoped agent interaction

## Status

Accepted direction by the Owner on 2026-10-08; implementation and validation
remain candidate evidence until recorded in the acceptance report.

## Context

The Owner wants to use an existing authenticated Grok CLI for all four Novel
Engine AI steps, permit supporting-file tools, and share the connection service
with trusted local and container clients. A direct child process inside each
Studio request would work for one host but would not meet the shared-service
requirement. An OpenAI-compatible bridge would hide ACP permissions and tools.

ACP v1 specifies stdio. WebSocket is a custom transport, so clients that expect
stdio need a small connecting command. Supporting arbitrary launch commands
also makes this an Owner-operated process service, not a multi-user sandbox.

## Decision

Use the existing CLI executable for `acp serve` and `acp connect`. The proxy
authenticates WebSocket upgrades with a separate bearer token and launches one
stdio process per trusted client connection. A namespaced initialization
extension supplies the executable, argument array, and working directory.
The proxy consumes that extension and preserves the remaining ACP messages.

Generic proxy clients may use ACP tools and permissions. Novel Engine selects
its own launch configuration and model on the server, presents CLI permission
requests to the Owner, and limits its supporting-file interface to the
configured working directory. The service does not advertise tenant isolation
or infer OS isolation from a working directory.

The `ai` application port owns typed execution events and permission requests.
The Studio supplies request-scoped interaction and continues to own manuscript
acceptance, revisions, snapshots, and durable outcomes. Progress subscriptions
and permission decisions work for structured and streaming steps alike.

SQLite, secrets, and registered immutable export artifacts remain outside the
supporting-file tool workspace. Working-file writes do not create Revisions.
Cancellation and failed generation do not imply reversal of completed tool
effects. Once an agent prompt capable of side effects is submitted, transport
recovery cannot automatically replay it.

The proxy uses the existing host CLI authentication without copying it into a
container or project settings. CLI transcript retention remains the CLI's
existing behavior and is documented separately from Novel Engine's SQLite
authority.

## Consequences

The single CLI root and existing Studio workflows stay authoritative. ACP adds
one Provider and a small observation/permission surface, without a new database
schema, multi-tenant control plane, or competing application executable.

The Owner must configure a writable materials directory and an independent
proxy token. Grok compatibility is tested against the installed version; model,
usage, cancellation, and native tool behavior require protocol and runtime
evidence, rather than assumptions from a current help page.

Source: https://agentclientprotocol.com/protocol/v1/transports
